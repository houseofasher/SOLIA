"""Capability roadmap tests."""

from __future__ import annotations

from brain.capability_roadmap import (
    roadmap_snapshot,
    simulate_future_timeline,
    try_roadmap_answer,
)


def test_roadmap_snapshot_structure():
    snap = roadmap_snapshot()
    assert snap["micro_topics"] == 862
    assert snap["context_window"] == 1_000_000
    assert len(snap["capabilities"]) >= 10
    assert snap["status_counts"]["live"] >= 5


def test_simulate_future_timeline():
    sim = simulate_future_timeline(months_ahead=12)
    assert sim["months_ahead"] == 12
    assert len(sim["milestones"]) >= 3


def test_roadmap_answer_building():
    answer = try_roadmap_answer("What are you building?")
    assert answer is not None
    assert "862" in answer or "supervised" in answer.lower()


def test_roadmap_answer_frontier():
    answer = try_roadmap_answer("Are you better than GPT?")
    assert answer is not None
    assert "frontier" in answer.lower() or "grounded" in answer.lower()
