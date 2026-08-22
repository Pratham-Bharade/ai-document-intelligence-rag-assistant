"""
File: backend/app/rag/llm.py
Purpose: Multi-provider LLM service with Groq LPU, OpenAI fallback, and token streaming.
Why it exists: LLMs generate the final answers in RAG. To achieve production reliability
               and blazing speed, we support Groq (ultra-fast inference on Llama 3)
               with automatic fallback to OpenAI (GPT-4o) if rate limits or outages occur.
               We also support async token streaming for real-time UI typewriter effects.
Dependencies: groq, openai, pydantic, typing
"""

import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3.6-27b",
    "llama3-70b-8192"
]

# Standard Enterprise RAG System Prompt
DEFAULT_SYSTEM_PROMPT = """You are an accurate, helpful AI Document Intelligence Assistant.
Your task is to answer the user's question STRICTLY using the provided context excerpts below.

Follow these strict rules:
1. Grounding: Answer ONLY based on the facts directly mentioned in the Context. Do not use outside assumptions.
2. Insufficient Context: If the context does not contain enough information to fully answer the question, clearly state: "Based on the provided documents, I do not have enough information to answer this question." Do NOT fabricate facts.
3. Citations: When making a factual claim, cite the source page number if available (e.g. "[Page 3]").
4. Tone: Professional, direct, and concise.
"""


def format_rag_prompt(
    query: str,
    context_chunks: List[Dict[str, Any]],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
) -> List[Dict[str, str]]:
    """
    Constructs Chat Completion messages (system + user) injecting retrieved context.
    """
    if not context_chunks:
        formatted_context = "No relevant context found."
    else:
        context_parts = []
        for i, chunk in enumerate(context_chunks, start=1):
            page_info = f" (Page {chunk.get('page_number')})" if chunk.get("page_number") else ""
            meta = chunk.get("metadata", {})
            doc_info = f" [Doc: {meta.get('document_id', 'unknown')}]" if meta.get("document_id") else ""
            text = chunk.get("text", "").strip()
            context_parts.append(f"--- Excerpt {i}{doc_info}{page_info} ---\n{text}")
        formatted_context = "\n\n".join(context_parts)

    user_content = f"""<CONTEXT>
{formatted_context}
</CONTEXT>

<USER_QUESTION>
{query}
</USER_QUESTION>

Please answer the question using the context above."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]


class LLMServiceError(Exception):
    """Custom exception for LLM generation errors."""
    pass


class LLMService:
    """
    Unified LLM Client supporting Groq (primary) and OpenAI (fallback)
    with synchronous generation and asynchronous token streaming.
    """
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        groq_model: str = "openai/gpt-oss-120b",
        openai_model: str = "gpt-4o-mini",
        temperature: float = 0.1
    ):
        if groq_api_key is None:
            self.groq_api_key = settings.groq_api_key or os.environ.get("GROQ_API_KEY")
        else:
            self.groq_api_key = groq_api_key

        if openai_api_key is None:
            self.openai_api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
        else:
            self.openai_api_key = openai_api_key

        self.groq_model = groq_model
        self.openai_model = openai_model
        self.temperature = temperature

        self._groq_client = None
        self._openai_client = None

        if self.groq_api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")

        if self.openai_api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        force_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a non-streaming completion with automatic fallback.
        """
        # Try Groq first
        if (force_provider == "groq" or force_provider is None) and self._groq_client:
            models_to_try = [self.groq_model] + [m for m in GROQ_FALLBACK_MODELS if m != self.groq_model]
            for model_name in models_to_try:
                try:
                    response = self._groq_client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=max_tokens
                    )
                    choice = response.choices[0]
                    self.groq_model = model_name  # Save working model
                    return {
                        "content": choice.message.content or "",
                        "provider": "groq",
                        "model": model_name,
                        "finish_reason": choice.finish_reason
                    }
                except Exception as e:
                    if "model_not_found" in str(e) or "404" in str(e):
                        continue
                    logger.warning(f"Groq generation attempt failed ({e}). Trying next fallback...")

            if force_provider == "groq":
                raise LLMServiceError("All configured Groq models failed.")

        # Fallback to OpenAI
        if self._openai_client:
            try:
                response = self._openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens
                )
                choice = response.choices[0]
                return {
                    "content": choice.message.content or "",
                    "provider": "openai",
                    "model": self.openai_model,
                    "finish_reason": choice.finish_reason
                }
            except Exception as e:
                logger.error(f"OpenAI fallback failed: {e}")
                raise LLMServiceError(f"All LLM providers failed. Last error: {e}")

        raise LLMServiceError("No LLM providers configured or available.")

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024
    ):
        """
        Synchronous generator yielding text chunks as they arrive from the API.
        """
        if self._groq_client:
            models_to_try = [self.groq_model] + [m for m in GROQ_FALLBACK_MODELS if m != self.groq_model]
            for model_name in models_to_try:
                try:
                    stream = self._groq_client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=max_tokens,
                        stream=True
                    )
                    for chunk in stream:
                        delta = chunk.choices[0].delta.content if chunk.choices else ""
                        if delta:
                            yield delta
                    self.groq_model = model_name
                    return
                except Exception as e:
                    if "model_not_found" in str(e) or "404" in str(e):
                        continue
                    logger.warning(f"Groq streaming with {model_name} failed ({e}). Trying fallback...")

        # Fallback to OpenAI streaming
        if self._openai_client:
            try:
                stream = self._openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else ""
                    if delta:
                        yield delta
                return
            except Exception as e:
                logger.error(f"OpenAI stream generation failed: {e}")
                raise LLMServiceError(f"Streaming failed: {e}")

        raise LLMServiceError("No active LLM client available for streaming.")
