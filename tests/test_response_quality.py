"""Response quality audit tests."""

from __future__ import annotations

from brain.response_quality import (
    audit_response,
    infer_question_intent,
    is_directed_choice_question,
    is_forum_garbage,
    is_system_fallback,
    QuestionIntent,
)
from brain.system_messages import FALLBACK_CORPUS


def test_detects_forum_garbage():
    junk = (
        "If you had to choose, which religion?: May 20, 2022 · If I had to choose. "
        "Which religion would you choose?: Aug 21, 2014 · I chose Islam."
    )
    assert is_forum_garbage(junk) is True


def test_directed_choice_intent():
    q = "if you had to choose a religion, what religion would you choose"
    assert is_directed_choice_question(q) is True
    assert infer_question_intent(q) == QuestionIntent.DIRECTED_PERSONAL


def test_audit_flags_predict_forum_paste():
    payload = {
        "kind": "predict",
        "classification": {"confidence": 0.19, "label": "computer_science"},
    }
    junk = (
        "If you had to choose, which religion?: May 20, 2022 · If I had to choose. "
        "Which religion would you choose?: Aug 21, 2014 · I chose Islam."
    )
    audit = audit_response("if you had to choose a religion", junk, payload)
    assert audit.adequate is False
    assert "forum_garbage" in audit.reasons or "directed_missed" in audit.reasons


def test_audit_accepts_reflection_reply():
    payload = {"kind": "reflection"}
    reply = (
        "I wouldn't claim membership in any tradition. "
        "If you're forcing the choice, I'd lean toward Buddhism."
    )
    audit = audit_response("if you had to choose a religion", reply, payload)
    assert audit.adequate is True


def test_audit_flags_corpus_fallback():
    audit = audit_response("Why did the Roman Empire fall?", FALLBACK_CORPUS, {"kind": "predict"})
    assert audit.adequate is False
    assert "weak_fallback" in audit.reasons


def test_live_intent():
    assert infer_question_intent("What is happening with global shipping routes right now?") == QuestionIntent.LIVE
