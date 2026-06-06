"""Deterministic QA tests."""

from __future__ import annotations

from brain.deterministic_qa import is_arithmetic_question, try_arithmetic_answer


def test_two_plus_two():
    result = try_arithmetic_answer("What is 2+2")
    assert result is not None
    assert result["answer"] == "4"
    assert result["evaluator"] == "deterministic_arithmetic"


def test_two_plus_two_with_spaces():
    result = try_arithmetic_answer("What is 2 + 2?")
    assert result is not None
    assert result["answer"] == "4"


def test_multiplication():
    result = try_arithmetic_answer("calculate 10 * 5")
    assert result is not None
    assert result["answer"] == "50"


def test_not_arithmetic():
    assert try_arithmetic_answer("What is the capital of France") is None
    assert not is_arithmetic_question("Who are you")


def test_division_by_zero():
    assert try_arithmetic_answer("what is 1/0") is None
