"""
File: backend/tests/test_prompts.py
Purpose: Unit tests for Prompt Engineering templates, modes, and few-shot formatting.
"""

from app.rag.prompts import (
    PromptMode,
    QA_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    COMPARISON_SYSTEM_PROMPT,
    build_rag_messages,
    format_context_block
)


def test_format_context_block_empty():
    """Test empty context string generation."""
    assert format_context_block([]) == "No relevant context found."


def test_format_context_block_multiple():
    """Test formatting multiple excerpts with page numbers and document IDs."""
    chunks = [
        {"text": "Policy A", "page_number": 1, "metadata": {"document_id": "doc1"}},
        {"text": "Policy B", "page_number": 2, "metadata": {}}
    ]
    formatted = format_context_block(chunks)
    assert "--- Excerpt 1 [Doc: doc1] (Page 1) ---\nPolicy A" in formatted
    assert "--- Excerpt 2 (Page 2) ---\nPolicy B" in formatted


def test_build_rag_messages_qa_mode():
    """Test standard QA message generation."""
    chunks = [{"text": "Refunds take 5 days.", "page_number": 3}]
    messages = build_rag_messages(
        query="How long do refunds take?",
        context_chunks=chunks,
        mode=PromptMode.QA
    )
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "STRICT GROUNDING" in messages[0]["content"]
    assert "MANDATORY CITATIONS" in messages[0]["content"]
    assert "<CONTEXT>" in messages[1]["content"]
    assert "<USER_QUERY>" in messages[1]["content"]
    assert "How long do refunds take?" in messages[1]["content"]


def test_build_rag_messages_few_shot():
    """Test few-shot QA example injection."""
    chunks = [{"text": "Sample text", "page_number": 1}]
    messages = build_rag_messages(
        query="Sample question",
        context_chunks=chunks,
        mode=PromptMode.QA,
        few_shot=True
    )
    
    user_msg = messages[1]["content"]
    assert "<FEW_SHOT_EXAMPLES>" in user_msg
    assert "Medical reimbursement" in user_msg or "Example 1:" in user_msg


def test_build_rag_messages_modes():
    """Test Summary, Extraction, and Comparison modes apply their specific system instructions."""
    chunks = [{"text": "Doc text", "page_number": 1}]
    
    # Summary
    summary_msgs = build_rag_messages(query="Summarize this", context_chunks=chunks, mode=PromptMode.SUMMARY)
    assert "Executive Overview" in summary_msgs[0]["content"]
    
    # Extraction
    extract_msgs = build_rag_messages(query="Extract data", context_chunks=chunks, mode=PromptMode.EXTRACTION)
    assert "valid, parseable JSON" in extract_msgs[0]["content"]
    
    # Comparison
    compare_msgs = build_rag_messages(query="Compare A and B", context_chunks=chunks, mode=PromptMode.COMPARISON)
    assert "CONTRADICTIONS" in compare_msgs[0]["content"] or "Document A vs Document B" in compare_msgs[0]["content"]


def test_build_rag_messages_custom_instructions():
    """Test appending custom instructions to the system prompt."""
    messages = build_rag_messages(
        query="Explain something",
        context_chunks=[],
        mode=PromptMode.QA,
        custom_instructions="Respond in Spanish only."
    )
    
    assert "ADDITIONAL USER INSTRUCTIONS:" in messages[0]["content"]
    assert "Respond in Spanish only." in messages[0]["content"]
