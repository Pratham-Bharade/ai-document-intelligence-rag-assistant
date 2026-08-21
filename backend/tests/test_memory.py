"""
File: backend/tests/test_memory.py
Purpose: Unit tests for Conversation Memory, Sliding Window, and Query Reformulation.
"""

import pytest
from unittest.mock import MagicMock

from app.rag.memory import (
    ConversationMemoryManager,
    format_chat_history,
    rephrase_standalone_query
)
from app.rag.llm import LLMService


def test_format_chat_history_empty():
    """Empty message list returns empty string."""
    assert format_chat_history([]) == ""


def test_format_chat_history_sliding_window():
    """Test that only the most recent N turns are included."""
    messages = [
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Answer 1"},
        {"role": "user", "content": "Question 2"},
        {"role": "assistant", "content": "Answer 2"},
        {"role": "user", "content": "Question 3"},
        {"role": "assistant", "content": "Answer 3"}
    ]
    # Keep last 2 turns (4 messages)
    history = format_chat_history(messages, max_turns=2)
    
    assert "Question 1" not in history
    assert "User: Question 2" in history
    assert "Assistant: Answer 2" in history
    assert "User: Question 3" in history
    assert "Assistant: Answer 3" in history


def test_format_chat_history_character_budget():
    """Test trimming when character budget is exceeded."""
    messages = [
        {"role": "user", "content": "A" * 50},
        {"role": "assistant", "content": "B" * 50},
        {"role": "user", "content": "Recent Question"}
    ]
    # Budget only allows the most recent line
    history = format_chat_history(messages, max_turns=5, max_chars=30)
    assert "Recent Question" in history
    assert "A" * 50 not in history


def test_rephrase_standalone_query_empty_history():
    """If chat history is empty, return original question without LLM call."""
    mock_llm = MagicMock(spec=LLMService)
    res = rephrase_standalone_query("What is PTO?", "", mock_llm)
    
    assert res == "What is PTO?"
    assert mock_llm.generate.call_count == 0


def test_rephrase_standalone_query_with_history():
    """Test pronoun resolution via LLM rephrasing."""
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.return_value = {
        "content": "How many weeks does parental leave last?"
    }

    history = "User: What is parental leave?\nAssistant: Parental leave is time off for new parents."
    rephrased = rephrase_standalone_query("How many weeks does it last?", history, mock_llm)

    assert rephrased == "How many weeks does parental leave last?"
    assert mock_llm.generate.call_count == 1


def test_conversation_memory_manager():
    """Test full manager preparing contextual standalone query and history."""
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.return_value = {
        "content": "What is the policy for medical reimbursement?"
    }

    manager = ConversationMemoryManager(max_turns=2)
    messages = [
        {"role": "user", "content": "Tell me about medical reimbursement."},
        {"role": "assistant", "content": "Medical reimbursement covers up to $2,000."}
    ]

    standalone_q, formatted_hist = manager.prepare_contextual_query(
        question="How do I submit claims for it?",
        messages=messages,
        llm_service=mock_llm
    )

    assert standalone_q == "What is the policy for medical reimbursement?"
    assert "User: Tell me about medical reimbursement." in formatted_hist
