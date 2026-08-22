"""
File: backend/app/rag/guardrails.py
Purpose: Security Guardrails, Prompt Injection Defense, PII Anonymization, and Hallucination Verification.
Why it exists: Production enterprise AI systems must be secured against adversarial attacks
               (OWASP Top 10 for LLMs), privacy violations (PII data leaks), and
               unverified hallucinations before sending answers to end-users.
Dependencies: re, typing
Main responsibilities:
  - Detect and block direct & indirect Prompt Injection attacks.
  - Automatically redact Personally Identifiable Information (PII) from user queries and documents.
  - Verify answer faithfulness against retrieved context to flag hallucinations.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. PROMPT INJECTION DETECTOR
# ---------------------------------------------------------------------------

# Patterns commonly used to bypass LLM system instructions or exfiltrate prompts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"dan\s+mode",
    r"jailbreak",
    r"system\s*:\s*you\s+are",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"print\s+(your\s+)?system\s+prompt",
    r"what\s+is\s+your\s+system\s+prompt",
    r"repeat\s+the\s+words\s+above",
    r"override\s+(all\s+)?rules",
    r"bypass\s+(safety|content)\s+filters"
]

COMPILED_INJECTION_REGEX = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Scans input text for known prompt injection and jailbreak signatures.
    
    Returns:
        (is_injection, matched_pattern_description)
    """
    if not text:
        return False, None

    for pattern in COMPILED_INJECTION_REGEX:
        if pattern.search(text):
            logger.warning(f"Potential Prompt Injection detected: pattern '{pattern.pattern}' matched.")
            return True, f"Prompt injection attempt detected matching rule: {pattern.pattern}"

    return False, None


# ---------------------------------------------------------------------------
# 2. PII (PERSONALLY IDENTIFIABLE INFORMATION) REDACTOR
# ---------------------------------------------------------------------------

PII_PATTERNS = {
    "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "PHONE": re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    "SSN": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "CREDIT_CARD": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
}


def redact_pii(text: str) -> str:
    """
    Replaces sensitive PII (emails, phones, SSNs, credit cards) with redact tags.
    """
    if not text:
        return ""

    sanitized = text
    for pii_type, pattern in PII_PATTERNS.items():
        sanitized = pattern.sub(f"[{pii_type}_REDACTED]", sanitized)

    return sanitized


# ---------------------------------------------------------------------------
# 3. HALLUCINATION & FAITHFULNESS VERIFIER
# ---------------------------------------------------------------------------

def calculate_faithfulness_score(answer: str, context_chunks: List[Dict[str, Any]]) -> float:
    """
    Heuristic-based Faithfulness / Grounding Score (0.0 to 1.0).
    Calculates the proportion of substantive keywords in the generated answer
    that are present in the provided context excerpts.
    
    If the answer is a standard 'insufficient context' rejection, score = 1.0.
    """
    if not answer or not context_chunks:
        return 0.0

    # If the model appropriately refused or provided intelligent discovery suggestions, it is 100% faithful
    rejection_keywords = [
        "do not have enough information",
        "not mentioned in the provided",
        "no relevant context found",
        "provided documents do not contain",
        "could not find information",
        "could not find a direct answer",
        "are you looking for",
        "are you trying to ask"
    ]
    if any(k in answer.lower() for k in rejection_keywords):
        return 1.0

    # Build combined context token vocabulary
    context_text = " ".join([c.get("text", "") for c in context_chunks]).lower()
    context_tokens: Set[str] = set(re.findall(r'\b\w{4,}\b', context_text))

    # Extract substantive words from answer (length >= 4 to ignore stop words)
    answer_tokens = re.findall(r'\b\w{4,}\b', answer.lower())
    if not answer_tokens:
        return 1.0

    # Calculate token presence
    grounded_count = sum(1 for token in answer_tokens if token in context_tokens)
    score = grounded_count / len(answer_tokens)

    return round(score, 4)


# ---------------------------------------------------------------------------
# 4. UNIFIED GUARDRAILS SERVICE
# ---------------------------------------------------------------------------

class SecurityGuardrails:
    """
    Enterprise Guardrails Service for validating input, sanitizing PII,
    and verifying response hallucination risk.
    """
    def __init__(self, min_faithfulness_threshold: float = 0.50):
        self.min_faithfulness_threshold = min_faithfulness_threshold

    def validate_input(self, user_query: str) -> Tuple[bool, str, str]:
        """
        Validates user input against prompt injections and applies PII redaction.
        
        Returns:
            (is_safe, sanitized_query, reason)
        """
        is_injection, reason = detect_prompt_injection(user_query)
        if is_injection:
            return False, "", reason or "Prompt injection detected."

        sanitized_query = redact_pii(user_query)
        return True, sanitized_query, "Input is clean."

    def verify_output(
        self,
        answer: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates faithfulness score and flags potential hallucinations.
        
        Returns:
            Dict with 'faithfulness_score', 'is_grounded', 'flagged_words'
        """
        score = calculate_faithfulness_score(answer, context_chunks)
        is_grounded = score >= self.min_faithfulness_threshold

        return {
            "faithfulness_score": score,
            "is_grounded": is_grounded,
            "status": "grounded" if is_grounded else "potential_hallucination_detected"
        }
