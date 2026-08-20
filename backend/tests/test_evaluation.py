"""
File: backend/tests/test_evaluation.py
Purpose: Unit tests for RAG Triad Metrics (Context Relevance, Faithfulness, Answer Relevance).
"""

from app.rag.evaluation import (
    RAGEvaluator,
    calculate_context_relevance,
    calculate_faithfulness,
    calculate_answer_relevance
)


def test_context_relevance_high():
    """Relevant context containing question terms should score high."""
    query = "What is the policy for medical leave?"
    context = [{"text": "Company policy regarding medical leave specifies 10 paid days."}]
    
    score = calculate_context_relevance(query, context)
    assert score >= 0.75


def test_context_relevance_low():
    """Irrelevant context should score low."""
    query = "What is the policy for medical leave?"
    context = [{"text": "The server uses PostgreSQL 16 on Linux Ubuntu."}]
    
    score = calculate_context_relevance(query, context)
    assert score <= 0.25


def test_faithfulness_grounded():
    """Answer supported by context should score high faithfulness."""
    context = [{"text": "Standard work hours are 9am to 5pm."}]
    answer = "The standard work hours are 9am to 5pm [Page 1]."
    
    score = calculate_faithfulness(answer, context)
    assert score >= 0.80


def test_faithfulness_hallucinated():
    """Answer with facts not in context should score low faithfulness."""
    context = [{"text": "The company cafeteria serves pizza on Friday."}]
    answer = "Employees get a $5,000 annual bonus for every patent filed."
    
    score = calculate_faithfulness(answer, context)
    assert score <= 0.30


def test_answer_relevance_high():
    """Directly addressing the question should yield high answer relevance."""
    query = "What is the annual bonus amount?"
    answer = "The annual bonus amount is 10% of base salary."
    
    score = calculate_answer_relevance(query, answer)
    assert score >= 0.75


def test_evaluate_triplet_pass():
    """A high-quality RAG execution should pass all 3 triad metrics."""
    evaluator = RAGEvaluator(pass_threshold=0.60)
    
    report = evaluator.evaluate_triplet(
        question="How many vacation days do employees receive?",
        context_chunks=[{"text": "Employees receive 25 vacation days per calendar year."}],
        answer="Employees receive 25 vacation days per calendar year [Page 2]."
    )
    
    assert report["passed"] is True
    assert report["rag_triad_average"] >= 0.70
    assert report["context_relevance"] >= 0.60
    assert report["faithfulness"] >= 0.60
    assert report["answer_relevance"] >= 0.60


def test_evaluate_dataset_aggregation():
    """Test batch evaluation over a multi-case dataset."""
    evaluator = RAGEvaluator(pass_threshold=0.60)
    
    dataset = [
        # Case 1: High quality
        {
            "question": "What are the core work hours?",
            "context_chunks": [{"text": "Core work hours are 10am to 4pm."}],
            "answer": "Core work hours are 10am to 4pm [Page 1]."
        },
        # Case 2: Hallucinated
        {
            "question": "What is the cafeteria lunch menu?",
            "context_chunks": [{"text": "Cafeteria serves sandwiches."}],
            "answer": "The CEO announced quarterly stock dividends of $5."
        }
    ]
    
    summary = evaluator.evaluate_dataset(dataset)
    
    assert summary["total_cases"] == 2
    assert summary["passed_cases"] == 1
    assert summary["pass_rate"] == 0.50
    assert "mean_triad_score" in summary
    assert len(summary["individual_reports"]) == 2
