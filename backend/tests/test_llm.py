"""
File: backend/tests/test_llm.py
Purpose: Unit tests for LLMService, prompt formatting, streaming, and failover.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.rag.llm import (
    DEFAULT_SYSTEM_PROMPT,
    LLMService,
    LLMServiceError,
    format_rag_prompt
)


def test_format_rag_prompt_empty_context():
    """Test prompt structure when no context chunks are found."""
    messages = format_rag_prompt(query="What is the policy?", context_chunks=[])
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "No relevant context found." in messages[1]["content"]
    assert "What is the policy?" in messages[1]["content"]


def test_format_rag_prompt_with_chunks():
    """Test that context chunks with page numbers are cleanly injected into user message."""
    chunks = [
        {
            "text": "Remote work is permitted on Fridays.",
            "page_number": 4,
            "metadata": {"document_id": "hr_policy_v2"}
        },
        {
            "text": "Core office hours are 10 AM to 4 PM.",
            "page_number": 5,
            "metadata": {}
        }
    ]
    messages = format_rag_prompt(query="Can I work from home?", context_chunks=chunks)
    
    user_content = messages[1]["content"]
    assert "Excerpt 1 [Doc: hr_policy_v2] (Page 4)" in user_content
    assert "Remote work is permitted on Fridays." in user_content
    assert "Excerpt 2 (Page 5)" in user_content
    assert "Can I work from home?" in user_content


def test_llm_generate_groq_success():
    """Test standard completion using Groq provider."""
    service = LLMService(groq_api_key="mock_groq_key")
    
    # Mock Groq client response
    mock_choice = MagicMock()
    mock_choice.message.content = "You can work from home on Fridays [Page 4]."
    mock_choice.finish_reason = "stop"
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    service._groq_client.chat.completions.create = MagicMock(return_value=mock_response)
    
    result = service.generate(messages=[{"role": "user", "content": "Hi"}])
    
    assert result["provider"] == "groq"
    assert result["content"] == "You can work from home on Fridays [Page 4]."
    assert result["finish_reason"] == "stop"


def test_llm_generate_fallback_to_openai():
    """Test that when Groq raises an exception, the service falls back to OpenAI."""
    service = LLMService(groq_api_key="mock_groq_key", openai_api_key="mock_openai_key")
    
    # Groq fails with 429 Rate Limit
    service._groq_client.chat.completions.create = MagicMock(side_effect=Exception("Rate limit reached"))
    
    # OpenAI succeeds
    mock_choice = MagicMock()
    mock_choice.message.content = "OpenAI fallback response."
    mock_choice.finish_reason = "stop"
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    service._openai_client.chat.completions.create = MagicMock(return_value=mock_response)
    
    result = service.generate(messages=[{"role": "user", "content": "Hi"}])
    
    assert result["provider"] == "openai"
    assert result["content"] == "OpenAI fallback response."


def test_llm_stream_generate():
    """Test generator yielding streaming token deltas."""
    service = LLMService(groq_api_key="mock_groq_key")
    
    # Mock streaming response chunks
    c1 = MagicMock(); c1.choices = [MagicMock(delta=MagicMock(content="Hello "))]
    c2 = MagicMock(); c2.choices = [MagicMock(delta=MagicMock(content="world!"))]
    
    service._groq_client.chat.completions.create = MagicMock(return_value=[c1, c2])
    
    tokens = list(service.stream_generate(messages=[{"role": "user", "content": "Hi"}]))
    
    assert tokens == ["Hello ", "world!"]


def test_llm_service_no_providers():
    """Test error when no API keys are provided."""
    service = LLMService(groq_api_key="", openai_api_key="")
    with pytest.raises(LLMServiceError, match="No LLM providers configured"):
        service.generate(messages=[{"role": "user", "content": "Hi"}])
