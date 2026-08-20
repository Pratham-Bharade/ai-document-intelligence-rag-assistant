"""
File: backend/app/rag/evaluation.py
Purpose: RAG Triad Evaluation & Benchmarking Engine.
Why it exists: You cannot improve what you cannot measure. When you tweak chunk size,
               overlap, or prompt templates, you need an objective mathematical benchmark
               to prove whether system quality improved or degraded (Regression Testing).
Dependencies: re, typing, numpy
Main responsibilities:
  - Calculate the 3 pillars of the RAG Triad:
      1. Context Relevance: Did we retrieve the right information for the question?
      2. Faithfulness / Groundedness: Is the answer derived strictly from the context?
      3. Answer Relevance: Does the answer directly solve the user's question?
  - Execute automated benchmark evaluation suites over golden test datasets.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. RAG TRIAD METRIC CALCULATORS
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "what", "where", "when", "which", "who", "whom", "whose", "why", "how",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "the", "a", "an", "and", "or", "but", "in", "on",
    "at", "to", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "from", "up", "down", "in",
    "out", "over", "under", "again", "further", "then", "once", "here", "there"
}


def calculate_context_relevance(question: str, context_chunks: List[Dict[str, Any]]) -> float:
    """
    Pillar 1: Context Relevance (0.0 to 1.0)
    Measures the proportion of substantive query terms present in the retrieved context.
    High score = The retrieval step found chunks directly relating to the query.
    """
    if not question.strip() or not context_chunks:
        return 0.0

    raw_tokens = re.findall(r'\b\w{3,}\b', question.lower())
    query_tokens = set(t for t in raw_tokens if t not in STOP_WORDS)
    if not query_tokens:
        query_tokens = set(raw_tokens)
    if not query_tokens:
        return 1.0

    context_text = " ".join([c.get("text", "") for c in context_chunks]).lower()
    
    matches = sum(1 for token in query_tokens if token in context_text)
    return round(matches / len(query_tokens), 4)


def calculate_faithfulness(answer: str, context_chunks: List[Dict[str, Any]]) -> float:
    """
    Pillar 2: Faithfulness / Groundedness (0.0 to 1.0)
    Measures whether the generated answer claims are supported by the context.
    Low score = Hallucination.
    """
    if not answer.strip() or not context_chunks:
        return 0.0

    # Proper out-of-context refusal is 100% faithful
    refusal_cues = ["do not have enough information", "not mentioned in", "no relevant context"]
    if any(cue in answer.lower() for cue in refusal_cues):
        return 1.0

    # Strip citation tags like [Page 1] or [Doc: handbook, Page 3] before evaluating tokens
    clean_answer = re.sub(r'\[(page|doc)[^\]]*\]', '', answer, flags=re.IGNORECASE)

    context_text = " ".join([c.get("text", "") for c in context_chunks]).lower()
    context_tokens = set(re.findall(r'\b\w{4,}\b', context_text))

    answer_tokens = [t for t in re.findall(r'\b\w{4,}\b', clean_answer.lower()) if t not in STOP_WORDS]
    if not answer_tokens:
        return 1.0

    grounded_count = sum(1 for t in answer_tokens if t in context_tokens)
    return round(grounded_count / len(answer_tokens), 4)


def calculate_answer_relevance(question: str, answer: str) -> float:
    """
    Pillar 3: Answer Relevance (0.0 to 1.0)
    Measures whether the answer addresses the question rather than digressing.
    """
    if not question.strip() or not answer.strip():
        return 0.0

    # Refusal to an unanswerable question is relevant
    refusal_cues = ["do not have enough information", "not mentioned in", "no relevant context"]
    if any(cue in answer.lower() for cue in refusal_cues):
        return 1.0

    raw_tokens = re.findall(r'\b\w{3,}\b', question.lower())
    query_tokens = set(t for t in raw_tokens if t not in STOP_WORDS)
    if not query_tokens:
        query_tokens = set(raw_tokens)
    if not query_tokens:
        return 1.0

    answer_text = answer.lower()
    overlap_count = sum(1 for token in query_tokens if token in answer_text)
    
    return round(overlap_count / len(query_tokens), 4)


# ---------------------------------------------------------------------------
# 2. RAG TRIAD EVALUATOR & BENCHMARK SUITE
# ---------------------------------------------------------------------------

class RAGEvaluator:
    """
    Evaluates single query-context-response triplets and runs benchmark datasets.
    """
    def __init__(self, pass_threshold: float = 0.60):
        self.pass_threshold = pass_threshold

    def evaluate_triplet(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        answer: str
    ) -> Dict[str, Any]:
        """
        Evaluates a single RAG execution across all 3 RAG Triad dimensions.
        """
        c_rel = calculate_context_relevance(question, context_chunks)
        faith = calculate_faithfulness(answer, context_chunks)
        a_rel = calculate_answer_relevance(question, answer)
        
        avg_score = round((c_rel + faith + a_rel) / 3.0, 4)
        passed = (c_rel >= self.pass_threshold and 
                  faith >= self.pass_threshold and 
                  a_rel >= self.pass_threshold)

        return {
            "context_relevance": c_rel,
            "faithfulness": faith,
            "answer_relevance": a_rel,
            "rag_triad_average": avg_score,
            "passed": passed
        }

    def evaluate_dataset(
        self,
        dataset: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Runs evaluation over a list of test cases and computes aggregate statistics.
        Each test case dict must have: 'question', 'context_chunks', 'answer'.
        """
        if not dataset:
            return {"total_cases": 0, "pass_rate": 0.0, "mean_triad_score": 0.0}

        results = []
        for case in dataset:
            report = self.evaluate_triplet(
                question=case["question"],
                context_chunks=case.get("context_chunks", []),
                answer=case["answer"]
            )
            results.append(report)

        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        mean_c_rel = round(sum(r["context_relevance"] for r in results) / total, 4)
        mean_faith = round(sum(r["faithfulness"] for r in results) / total, 4)
        mean_a_rel = round(sum(r["answer_relevance"] for r in results) / total, 4)
        mean_avg = round(sum(r["rag_triad_average"] for r in results) / total, 4)

        return {
            "total_cases": total,
            "passed_cases": passed_count,
            "pass_rate": round(passed_count / total, 4),
            "mean_context_relevance": mean_c_rel,
            "mean_faithfulness": mean_faith,
            "mean_answer_relevance": mean_a_rel,
            "mean_triad_score": mean_avg,
            "individual_reports": results
        }
