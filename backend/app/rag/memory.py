"""
File: backend/app/rag/memory.py
Purpose: Multi-Turn Conversation Memory, Sliding Window Buffering, and Query Reformulation.
Why it exists: In real chat applications, users ask follow-up questions with pronouns:
               Turn 1: "What is the policy on maternity leave?"
               Turn 2: "How many weeks does it last?"
               If we search our vector database for "How many weeks does it last?",
               vector search returns irrelevant results because "it" has no semantic meaning.
               We use Query Contextualization to rewrite Turn 2 into:
               "How many weeks does maternity leave last?" before running vector retrieval.
Dependencies: typing, re
Main responsibilities:
  - Format chronological chat history into sliding-window text buffers.
  - Enforce character/token limits on conversation history.
  - Reformulate ambiguous follow-up questions into standalone search queries.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from app.rag.llm import LLMService

logger = logging.getLogger(__name__)


REPHRASE_SYSTEM_PROMPT = """You are an expert Query Reformulation Assistant.
Given a chat history between a user and an AI assistant, and a follow-up question from the user, your task is to rewrite the follow-up question into a standalone, independent search query.

CRITICAL OPERATING RULES:
1. Resolve all pronouns (e.g. "it", "they", "that", "this policy", "the former", "the latter") to their explicit referents from the chat history.
2. DO NOT answer the question.
3. DO NOT add new information or assumptions.
4. Output ONLY the reformulated query text without quotes or explanations.
5. If the question is already standalone and does not depend on the chat history, return it verbatim.
"""


def format_chat_history(
    messages: List[Dict[str, Any]],
    max_turns: int = 5,
    max_chars: int = 2000
) -> str:
    """
    Takes a list of message dicts/models and formats the most recent N turns
    into a clean dialogue string within a strict character budget.
    """
    if not messages:
        return ""

    # Slice most recent messages (each turn is user + assistant = 2 messages)
    recent_messages = messages[-(max_turns * 2):]
    
    formatted_lines = []
    total_chars = 0

    for msg in reversed(recent_messages):
        role_label = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "").strip()
        line = f"{role_label}: {content}"
        
        if total_chars + len(line) > max_chars:
            break
            
        formatted_lines.insert(0, line)
        total_chars += len(line)

    return "\n".join(formatted_lines)


def rephrase_standalone_query(
    question: str,
    chat_history: str,
    llm_service: LLMService
) -> str:
    """
    Uses the LLM to rewrite a pronoun-heavy follow-up question into a standalone query.
    If chat history is empty, returns the question as-is.
    """
    if not chat_history.strip() or not question.strip():
        return question

    prompt_messages = [
        {"role": "system", "content": REPHRASE_SYSTEM_PROMPT},
        {"role": "user", "content": f"<CHAT_HISTORY>\n{chat_history}\n</CHAT_HISTORY>\n\n<FOLLOW_UP_QUESTION>\n{question}\n</FOLLOW_UP_QUESTION>\n\nStandalone Query:"}
    ]

    try:
        response = llm_service.generate(messages=prompt_messages, max_tokens=128)
        rephrased = response.get("content", "").strip()
        if rephrased:
            logger.info(f"Rephrased query: '{question}' -> '{rephrased}'")
            return rephrased
        return question
    except Exception as e:
        logger.warning(f"Query rephrasing failed ({e}), falling back to raw question.")
        return question


class ConversationMemoryManager:
    """
    Manages chat history windowing and query contextualization.
    """
    def __init__(self, max_turns: int = 5, max_chars: int = 2000):
        self.max_turns = max_turns
        self.max_chars = max_chars

    def prepare_contextual_query(
        self,
        question: str,
        messages: List[Dict[str, Any]],
        llm_service: LLMService
    ) -> Tuple[str, str]:
        """
        Formats history and produces a standalone retrieval query.
        
        Returns:
            (standalone_query, formatted_chat_history)
        """
        history_text = format_chat_history(
            messages=messages,
            max_turns=self.max_turns,
            max_chars=self.max_chars
        )
        
        standalone_query = rephrase_standalone_query(
            question=question,
            chat_history=history_text,
            llm_service=llm_service
        )

        return standalone_query, history_text
