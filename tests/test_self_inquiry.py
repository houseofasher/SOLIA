"""Self-inquiry tests."""

from __future__ import annotations

from brain.self_inquiry import (
    answer_question,
    generate_questions,
    is_self_inquiry_enabled,
    recent_inquiries,
    reset_batch_inquiry_budget,
    run_self_inquiry_for_cycle,
)


def test_generate_questions_for_physics():
    qs = generate_questions(
        domain_slug="science_and_natural_philosophy",
        subdomain_slug="physics",
        micro_slug="classical_mechanics",
        grade_slug="preschool",
        count=2,
    )
    assert len(qs) == 2
    assert all("?" in q for q in qs)


def test_self_inquiry_runs_after_cycle(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_SELF_INQUIRY", "1")
    monkeypatch.setenv("AUREON_DATA_DIR", str(tmp_path))
    reset_batch_inquiry_budget(limit=10)

    outcome = {
        "domain": "science_and_natural_philosophy",
        "subdomain": "physics",
        "micro_subdomain": "classical_mechanics",
        "grade": "preschool",
        "grade_name": "Pre-School",
        "graduation": {"passed": True, "unlocked_next": "elementary", "train_accuracy": 0.0},
        "regions": [
            {"region": "collector", "status": "completed", "metrics": {}},
            {"region": "trainer", "status": "skipped", "metrics": {"reason": "need at least 2 classes"}},
        ],
    }
    exchanges = run_self_inquiry_for_cycle(outcome)
    assert len(exchanges) == 2
    assert exchanges[0]["question"]
    assert "Asking myself" in exchanges[0]["answer"]
    assert len(recent_inquiries(5)) == 2


def test_self_inquiry_disabled(monkeypatch):
    monkeypatch.setenv("AUREON_SELF_INQUIRY", "0")
    assert is_self_inquiry_enabled() is False
    reset_batch_inquiry_budget(limit=10)
    outcome = {
        "domain": "science_and_natural_philosophy",
        "subdomain": "physics",
        "micro_subdomain": "classical_mechanics",
        "grade": "preschool",
        "graduation": {"passed": True},
        "regions": [],
    }
    assert run_self_inquiry_for_cycle(outcome) == []


def test_answer_question_mentions_regions():
    answer = answer_question(
        "What is classical mechanics?",
        outcome={
            "grade_name": "Pre-School",
            "graduation": {"passed": True, "unlocked_next": "elementary"},
            "regions": [{"region": "reward", "status": "completed", "metrics": {}}],
        },
    )
    assert "reward" in answer
    assert "unlocked elementary" in answer.lower()
