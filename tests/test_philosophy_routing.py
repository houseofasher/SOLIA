"""Philosophy routing must not swallow technical questions."""

from __future__ import annotations

from brain.philosophy_handler import is_philosophy_question


def test_algorithms_purpose_is_not_philosophy():
    assert is_philosophy_question("What are the purpose of algorithms") is False


def test_life_purpose_is_philosophy():
    assert is_philosophy_question("What is the purpose of life") is True
