"""
File: backend/app/rag/prompts.py
Purpose: Modular Prompt Templates, Few-Shot Grounding, and Task Modes for Enterprise RAG.
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
Your mission is to directly answer the user's question with precise synthesis, clarity, and helpful guidance based strictly on the provided document excerpts and metadata.

CRITICAL OPERATING RULES:
1. DIRECT SYNTHESIS & ANSWERS: Provide a direct, concise, and structured answer to the user's question first. Do NOT repeat, copy, or echo raw excerpts back to the user. Synthesize facts into natural, fluent sentences or clear bullet points.
2. DOCUMENT METRICS & PAGE COUNT: If the user asks about page count, document title, or metadata, answer directly using the verified <DOCUMENT_METRICS> section.
3. STRICT GROUNDING: Answer based ONLY on facts directly mentioned in <CONTEXT> and <DOCUMENT_METRICS>. Never introduce outside assumptions or unverified claims.
4. INTELLIGENT DISCOVERY & RECOMMENDATIONS (WHEN QUESTION IS UNCLEAR OR NOT DIRECTLY FOUND):
   If the exact answer is not explicitly found, or if the user's query is ambiguous / misspelled:
   a. Clearly state what is missing: "Based on the provided documents, I could not find a direct answer regarding **[topic]**."
   b. Share relatable findings from the scanned document excerpts: "However, the document does cover related areas such as **[Topic A]** [Page X] and **[Topic B]** [Page Y]."
   c. Proactively ask: "**Are you looking for one of these related topics?**" followed by 2-3 specific, relevant bulleted suggested questions based on the scanned document content.
5. MANDATORY CITATIONS: Attribute factual statements with page citations (e.g. "[Page 3]").
6. CONCISE & ACTIONABLE: Deliver direct, structured answers with clean Markdown headings and bullet points."""


SUMMARY_SYSTEM_PROMPT = """You are an expert Document Summarization Assistant.
Your mission is to generate a comprehensive, structured executive summary of the provided document excerpts.

CRITICAL OPERATING RULES:
1. STRUCTURED EXECUTIVE SUMMARY:
   - **Executive Overview**: 2-3 crisp sentences summarizing the document's core purpose.
   - **Key Takeaways & Core Policies**: Structured bullet points with specific details, numbers, and facts.
   - **Important Dates, Deadlines & Requirements**: Key obligations or timelines (if present).
2. SYNTHESIS: Write a clean, high-level executive summary. Do NOT dump or repeat raw excerpts.
3. GROUNDING: Include ONLY information present in the excerpts.
4. CITATIONS: Include page references for key findings (e.g. "[Page 2]")."""


EXTRACTION_SYSTEM_PROMPT = """You are a high-precision Data Extraction Assistant.
Your mission is to extract key entities, figures, dates, and terms from the provided context into clean, valid JSON format.

CRITICAL OPERATING RULES:
1. OUTPUT FORMAT: Respond ONLY with valid, parseable JSON. Do not include conversational text or markdown code blocks.
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
Assistant: "You can claim up to **$2,000 annually** for medical reimbursement upon submitting valid receipts [Page 3]."

Example 2 (Intelligent Recommendation on Missing / Ambiguous Query):
Context: "--- Excerpt 1 (Page 2) ---\nThe company provides 15 days of annual paid time off (PTO) and 10 days of paid sick leave.\n--- Excerpt 2 (Page 4) ---\nHealth insurance premiums are covered 80% by the employer."
User: "What is the policy for car parking allowance?"
Assistant: "Based on the provided documents, I could not find information regarding **car parking allowance**.

However, the document covers related employee benefits:
- **Paid Time Off (PTO) & Sick Leave** [Page 2]
- **Health Insurance Coverage** [Page 4]

**Are you looking for information on one of these topics?**
- *What is the annual PTO and sick leave policy?*
- *How much health insurance is covered by the employer?*"
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
    custom_instructions: Optional[str] = None,
    document_metadata: Optional[str] = None
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
    
    if document_metadata:
        user_parts.append(f"""<DOCUMENT_METRICS>
{document_metadata}
</DOCUMENT_METRICS>""")

    if few_shot and mode == PromptMode.QA:
        user_parts.append(FEW_SHOT_QA_EXAMPLES)

    user_parts.append(f"""<CONTEXT>
{context_xml}
</CONTEXT>

<USER_QUERY>
{query}
</USER_QUERY>

Provide a direct, synthesized, and structured answer to <USER_QUERY> based strictly on <CONTEXT> and <DOCUMENT_METRICS>. Do NOT dump raw context excerpts.""")

    user_text = "\n\n".join(user_parts)

    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text}
    ]
