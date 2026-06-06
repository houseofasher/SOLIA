"""Combinatorial creation doctrine tests."""

from __future__ import annotations

from app.chat_service import chat
from brain.combinatorial_creation import (
    handle_creation_request,
    is_creation_request,
    plan_combinatorial_creation,
)


def test_is_creation_request():
    assert is_creation_request("create a new cure for cancer")
    assert is_creation_request("invent a new algorithm for sorting")
    assert not is_creation_request("what is the capital of france")


def test_plan_has_two_precursors():
    plan = plan_combinatorial_creation("create a new medicine for diabetes")
    assert plan.to_dict()["valid"] is True
    assert len(plan.precursors) >= 2


def test_handle_creation_request():
    payload = handle_creation_request("design a new software system for verification")
    assert payload["kind"] == "combinatorial_creation"
    assert payload["combinatorial"]["valid"] is True
    assert "Parent 1" in payload["reply"]


def test_chat_creation_route():
    result = chat("create a new algorithm that combines retrieval and verification")
    assert result["kind"] == "combinatorial_creation"
    assert "combinatorial" in result
