"""Predict brain abstains in live-only mode until corpus is dense enough."""

from __future__ import annotations

import brain.predict_engine as pe
from brain.predict_engine import predict_with_steps


def test_predict_abstains_when_live_corpus_thin(monkeypatch):
    monkeypatch.setenv("AUREON_LIVE_ONLY", "1")
    monkeypatch.setenv("AUREON_PREDICT_MIN_DOCS", "5")
    monkeypatch.setattr(pe, "_corpus_document_count", lambda: 0)
    monkeypatch.setattr(pe, "_model", None)
    monkeypatch.setattr(pe, "_ready", False)

    result = predict_with_steps("What is quantum mechanics?", force=True)
    assert result is not None
    assert result.get("abstained") is True
