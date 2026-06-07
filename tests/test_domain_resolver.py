"""Domain resolver and corpus answer tests."""

from __future__ import annotations

from brain.corpus_answer import answer_from_corpus_hits
from brain.domain_resolver import is_knowledge_question, resolve_crawl_domain
from brain.vector_rag import RagHit


def test_resolve_biology_over_classifier():
    domain = resolve_crawl_domain(
        "What is the point of human evolution and what drives it biologically?",
        classifier_label="computer_science",
    )
    assert domain == "biology"


def test_resolve_history_question():
    domain = resolve_crawl_domain(
        "What were the real causes behind the fall of the Roman Empire?",
        classifier_label="computer_science",
    )
    assert domain == "history"


def test_resolve_ai_question():
    domain = resolve_crawl_domain(
        "What are the main types of machine learning algorithms and how do they differ?",
        classifier_label="computer_science",
    )
    assert domain == "artificial_intelligence"


def test_corpus_answer_from_hits():
    hits = [
        RagHit(
            1,
            "abc",
            "Evolution",
            (
                "Natural selection drives human evolution by favoring traits that improve survival. "
                "Genetic variation within populations provides raw material for adaptation over time. "
                "Environmental pressures shape which alleles become more common across generations."
            ),
            "omnispider:https://www.britannica.com/science/evolution",
            0.5,
        ),
    ]
    answer = answer_from_corpus_hits(
        "What is the point of human evolution and what drives it biologically?",
        hits,
    )
    assert answer
    assert "natural selection" in answer.lower() or "genetic" in answer.lower()


def test_is_knowledge_question():
    assert is_knowledge_question("What is quantum mechanics?")
    assert not is_knowledge_question("hi")
