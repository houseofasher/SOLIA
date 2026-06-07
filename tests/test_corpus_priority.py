"""Corpus gap prioritization for auto-learn."""

from __future__ import annotations

from brain import corpus_priority as cp
from brain.corpus_priority import sort_targets_by_corpus_gap


def test_sort_targets_by_corpus_gap_prefers_empty_topics(monkeypatch):
    targets = [
        ("physics", "quantum", "entanglement"),
        ("history", "ancient", "rome"),
    ]
    monkeypatch.setattr(
        cp,
        "document_counts_for_targets",
        lambda _targets: {
            ("physics", "quantum", "entanglement"): 4,
            ("history", "ancient", "rome"): 0,
        },
    )
    ordered = sort_targets_by_corpus_gap(targets)
    assert ordered[0] == ("history", "ancient", "rome")
    assert ordered[1] == ("physics", "quantum", "entanglement")
