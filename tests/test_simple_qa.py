"""Simple Question, Simple Answer policy tests."""

from __future__ import annotations

from brain.simple_qa import is_simple_question, to_simple_answer


def test_is_simple_question():
    assert is_simple_question("What is botany?")
    assert is_simple_question("What are you learning?")
    assert not is_simple_question("/status")
    assert not is_simple_question(" " * 5 + "Explain in detail the full history of quantum mechanics and its mathematical foundations across all domains")


def test_to_simple_answer_one_sentence():
    text = "Botany is plants. Passed Pre-School with 100% accuracy."
    assert to_simple_answer(text) == "Botany is plants."


def test_to_simple_answer_truncates():
    long = "A" * 200
    out = to_simple_answer(long, max_len=40)
    assert len(out) <= 41
    assert out.endswith(".")
