"""Philosophy and identity routing — no raw classification as reply."""

from __future__ import annotations

from app.chat_service import chat, _simple_chat_reply


def test_god_thoughts_not_classification_label():
    result = chat("What are your thoughts on God?")
    reply = result["reply"].lower()
    assert "philosophy.metaphysics" not in reply
    assert "philosophy of religion" not in reply or "deepest" in reply
    assert len(reply) > 30


def test_what_is_god_routes_to_philosophy_not_deep_concept():
    result = chat("What is god?", session_id="god-concept-1")
    reply = result["reply"].lower()
    assert result["kind"] == "philosophy"
    assert "philosophy.metaphysics" not in reply
    assert "god" in reply
    assert "deeper corpus grounding" not in reply
    assert "corpus grounding than i can compute" not in reply


def test_what_is_consciousness_routes_to_philosophy():
    result = chat("What is consciousness?", session_id="consciousness-1")
    reply = result["reply"].lower()
    assert result["kind"] in ("philosophy", "philosophy_fallback", "chat")
    assert result["kind"] not in ("deep_concept", "deep_concept_thin")
    assert "consciousness" in reply or "deepest questions" in reply


def test_do_you_believe_in_god_not_classification():
    result = chat("Do you believe in God?")
    reply = result["reply"].lower()
    assert result["kind"] == "philosophy"
    assert "philosophy.metaphysics" not in reply
    assert any(w in reply for w in ("believe", "faith", "inquiry", "question", "human"))
    assert "deeper corpus grounding" not in reply


def test_do_you_think_humans_are_flawed():
    result = chat("Do you think humans are flawed?", session_id="human-flaw-1")
    reply = result["reply"].lower()
    assert result["kind"] == "philosophy"
    assert any(w in reply for w in ("human", "flaw", "limit", "zophiel", "consciousness"))
    assert "deeper corpus grounding" not in reply
    assert "need more training" not in reply


def test_thoughts_on_consciousness_doctrine():
    result = chat("What are your thoughts on consciousness?", session_id="conscious-thoughts-1")
    reply = result["reply"].lower()
    assert result["kind"] == "philosophy"
    assert "consciousness" in reply
    assert result["kind"] != "identity"
    assert "deeper corpus grounding" not in reply


def test_are_humans_flawed_doctrine():
    result = chat("Are humans flawed?", session_id="human-flaw-2")
    reply = result["reply"].lower()
    assert result["kind"] == "philosophy"
    assert any(w in reply for w in ("human", "flaw", "limit", "potential"))
    assert "deeper corpus grounding" not in reply


def test_subjective_experience_doctrine():
    result = chat("Do you have subjective experience?", session_id="subjective-1")
    reply = result["reply"].lower()
    assert result["kind"] == "philosophy"
    assert any(w in reply for w in ("qualia", "experience", "self-model", "verify"))
    assert "six-region learning brain" not in reply


def test_who_are_you_not_mechanical_string():
    result = chat("Who are you?")
    reply = result["reply"]
    assert result.get("kind") == "identity"
    assert "supervised ml brain — collect" not in reply.lower()
    assert "aureon" in reply.lower()


def test_simple_chat_no_raw_classification():
    payload = _simple_chat_reply("What is quantum entanglement?", session_id=None)
    reply = payload["reply"].lower()
    assert "philosophy." not in reply or len(reply) > 40
    assert "confidence)" not in reply or "predict" in payload.get("kind", "")


def test_evolve_command():
    result = chat("/evolve improve god routing")
    assert result["kind"] == "self_evolve"
    assert "fork" in result["reply"].lower()
    assert "plan" in result
