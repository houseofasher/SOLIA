"""Phase 4-5 feature tests."""

from __future__ import annotations

from pathlib import Path

from brain.agent_loop import is_agent_task, run_agent_loop
from brain.multimodal_collector import MultimodalCollector
from src.efficient_inference import attention_window, inference_profile, truncate_tokens_for_inference


def test_is_agent_task():
    assert is_agent_task("/agent search DNA")
    assert is_agent_task("first search then calculate 2+2")
    assert not is_agent_task("hello")


def test_agent_loop_runs_steps():
    result = run_agent_loop("What is 2+2", max_steps=5)
    assert result["agent"] is True
    assert "rag_search" in result["plan"]
    assert result["answer"] == "4"


def test_inference_profile_sparse():
    profile = inference_profile(10_000, window=512)
    assert profile["mode"] == "sliding_window"
    assert profile["speedup_vs_dense"] > 1


def test_truncate_tokens_for_inference():
    ids = list(range(1000))
    ids[0] = 2
    out = truncate_tokens_for_inference(ids, max_window=64)
    assert len(out) <= 64


def test_multimodal_json_manifest(tmp_path, monkeypatch):
    from pipeline import config

    monkeypatch.setattr(config, "MULTIMODAL_DIR", tmp_path)
    manifest = {
        "modality": "image",
        "title": "Cell diagram",
        "caption": "A diagram showing nucleus mitochondria and cell membrane structures for biology study.",
        "metadata": {"domain": "biology"},
    }
    (tmp_path / "cell.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
    docs = MultimodalCollector(inbox=tmp_path).collect(limit=5)
    assert len(docs) == 1
    assert docs[0].metadata["modality"] == "image"
