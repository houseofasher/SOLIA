"""Chat routing for deterministic QA and identity."""

from __future__ import annotations

import brain.predict_engine as pe
from app.chat_service import chat


def test_chat_who_are_you(client=None):
    del client
    result = chat("Who Are You", session_id="test")
    assert result["simple_qa"] is True
    assert "supervised" in result["reply"].lower()


def test_chat_two_plus_two(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(pe, "_model", None)
    monkeypatch.setattr(pe, "_ready", False)

    result = chat("What is 2+2", session_id="test")
    assert result.get("deterministic") is not None
    assert result["reply"] == "4"
    assert result["simple_qa"] is True
    assert not result.get("brain_predict")


def test_chat_roadmap_question():
    result = chat("What are you building?", session_id="test")
    assert result["simple_qa"] is True
    assert "862" in result["reply"] or "micro" in result["reply"].lower()
