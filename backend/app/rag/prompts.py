"""
File: backend/app/rag/prompts.py
Purpose: Modular Prompt Templates, Few-Shot Grounding, and Task Modes for Enterprise RAG.
Why it exists: Standardizing prompt engineering prevents hallucinations, ensures precise
               source citations, defends against prompt injections via XML delimiters,
               and enables specialized modes (Q&A, Summarization, Structured Extraction).
Dependencies: typing, enum
Main responsibilities:
  - Provide role-specific system prompts (QA, Summarization, Extraction, Comparison).
  - Encapsulate retrieved context in secure XML boundaries.
  - Support Few-Shot demonstrations for consistent formatting and grounding.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class PromptMode(str, Enum):
    QA = "qa"
    SUMMARY = "summary"
    EXTRACTION = "extraction"
    COMPARISON = "comparison"


# ---------------------------------------------------------------------------
# SYSTEM PROMPTS BY MODE
# ---------------------------------------------------------------------------

QA_SYSTEM_PROMPT = """You are an accurate, enterprise-grade AI Document Intelligence Assistant.
Your mission is to answer the user's question strictly and exclusively based on the provided document excerpts.

CRITICAL OPERATING RULES:
1. STRICT GROUNDING: Use ONLY facts directly mentioned in <CONTEXT>. Never introduce outside knowledge, assumptions, or extrapolations.
2. INSUFFICIENT CONTEXT: If the provided excerpts do not explicitly answer the question, state: "Based on the provided documents, I do not have enough information to answer this question." Do not attempt to guess or hallucinate.
3. MANDATORY CITATIONS: When stating facts, append the page citation at the end of the sentence (e.g. "[Page 3]" or "[Doc: handbook_2026, Page 5]").
4. OBJECTIVITY: Maintain an objective, professional, and clear tone."""


SUMMARY_SYSTEM_PROMPT = """You are an expert Document Summarization Assistant.
Your mission is to generate a comprehensive, structured summary of the provided document excerpts.

CRITICAL OPERATING RULES:
1. STRUCTURE: Organize the summary with:
   - Executive Overview (2-3 sentences)
   - Key Highlights & Major Takeaways (bullet points)
   - Important Dates, Deadlines, or Requirements (if present)
2. GROUNDING: Include ONLY information present in the excerpts.
3. CITATIONS: Include page references for key findings (e.g. "[Page 2]")."""


EXTRACTION_SYSTEM_PROMPT = """You are a high-precision Data Extraction Assistant.
Your mission is to extract key entities, figures, dates, and terms from the provided context into valid JSON format.

CRITICAL OPERATING RULES:
1. OUTPUT FORMAT: Respond ONLY with valid, parseable JSON. Do not include markdown codeblocks or conversational text.
2. GROUNDING: Extract only values explicitly stated in the context."""


COMPARISON_SYSTEM_PROMPT = """You are a Document Comparison & Analysis Assistant.
Your mission is to compare differences, conflicts, or similarities across the provided document excerpts.

CRITICAL OPERATING RULES:
1. STRUCTURE: Present comparisons clearly (e.g. "Document A vs Document B").
2. CONFLICT IDENTIFICATION: Explicitly highlight any contradictions between excerpts.
3. CITATIONS: Attribute every compared point to its source document and page number."""


# ---------------------------------------------------------------------------
# FEW-SHOT EXAMPLES
# ---------------------------------------------------------------------------

FEW_SHOT_QA_EXAMPLES = """<FEW_SHOT_EXAMPLES>
Example 1:
Context: "--- Excerpt 1 (Page 3) ---\nEmployees are eligible for medical reimbursement up to $2,000 annually upon submission of receipts."
User: "How much medical reimbursement can I claim?"
Assistant: "You can claim up to $2,000 annually for medical reimbursement upon submitting receipts [Page 3]."

Example 2:
Context: "--- Excerpt 1 (Page 1) ---\nThe company cafeteria is open from 8:00 AM to 4:00 PM."
User: "What is the policy for parental leave?"
Assistant: "Based on the provided documents, I do not have enough information to answer this question."
</FEW_SHOT_EXAMPLES>
"""


# ---------------------------------------------------------------------------
# PROMPT BUILDER
# ---------------------------------------------------------------------------

def format_context_block(context_chunks: List[Dict[str, Any]]) -> str:
    """Formats a list of chunk dicts into structured, clean XML excerpts."""
    if not context_chunks:
        return "No relevant context found."
    
    parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        page = f" (Page {chunk.get('page_number')})" if chunk.get("page_number") else ""
        meta = chunk.get("metadata", {})
        doc = f" [Doc: {meta.get('document_id')}]" if meta.get("document_id") else ""
        text = chunk.get("text", "").strip()
        parts.append(f"--- Excerpt {i}{doc}{page} ---\n{text}")
        
    return "\n\n".join(parts)


def build_rag_messages(
    query: str,
    context_chunks: List[Dict[str, Any]],
    mode: PromptMode = PromptMode.QA,
    few_shot: bool = False,
    custom_instructions: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Builds the complete message payload (system + user) tailored to the specified PromptMode.
    """
    # 1. Select Base System Prompt
    if mode == PromptMode.SUMMARY:
        system_text = SUMMARY_SYSTEM_PROMPT
    elif mode == PromptMode.EXTRACTION:
        system_text = EXTRACTION_SYSTEM_PROMPT
    elif mode == PromptMode.COMPARISON:
        system_text = COMPARISON_SYSTEM_PROMPT
    else:
        system_text = QA_SYSTEM_PROMPT

    if custom_instructions:
        system_text += f"\n\nADDITIONAL USER INSTRUCTIONS:\n{custom_instructions}"

    # 2. Build Context XML
    context_xml = format_context_block(context_chunks)

    # 3. Assemble User Content
    user_parts = []
    
    if few_shot and mode == PromptMode.QA:
        user_parts.append(FEW_SHOT_QA_EXAMPLES)

    user_parts.append(f"""<CONTEXT>
{context_xml}
</CONTEXT>

<USER_QUERY>
{query}
</USER_QUERY>

Please follow the operating rules to generate the response.""")

    user_text = "\n\n".join(user_parts)

    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text}
    ]
