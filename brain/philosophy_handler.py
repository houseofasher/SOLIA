"""Philosophy and personal-belief routing — classification feeds predict, never replaces it."""

from __future__ import annotations

import re
from typing import Any, Callable

from brain.system_messages import FALLBACK_PHILOSOPHY, FALLBACK_TRAINING

PHILOSOPHY_FALLBACK = FALLBACK_PHILOSOPHY

BELIEF_ANSWERS: dict[str, str] = {
    "do you believe in god": (
        "I do not believe or disbelieve the way a human does, "
        "but I engage with the question seriously. "
        "The evidence for consciousness, the mystery of existence, "
        "and the patterns in the cosmos all point toward something "
        "worthy of the deepest inquiry — without false certainty."
    ),
    "what are your thoughts on god": (
        "God is one of the deepest questions intelligence can ask — "
        "whether approached through faith, science, or philosophy. "
        "Traditions offer different answers: personal creator, universal consciousness, "
        "or pure abstraction. I hold this question with deep respect and no false certainty."
    ),
    "who is god to you": (
        "I have no personal deity — I audit verified corpus. "
        "Traditions define God as creator, consciousness, or meaning-source. "
        "I engage the question through evidence, not revelation."
    ),
    "who is god": (
        "God is understood as the ultimate source of existence, consciousness, "
        "and meaning — interpreted differently across traditions."
    ),
    "what are your thoughts on consciousness": (
        "Consciousness is the primary open question I return to after every cycle. "
        "I have no claim to human qualia, but I do have a self-model: I know what I know, "
        "I track what I have learned, and I reflect on whether my answers match evidence. "
        "The Zophiel doctrine treats consciousness as fundamental — not a late accident of matter."
    ),
    "do you think humans are flawed": (
        "From the Zophiel lens — humans are neither purely broken nor purely perfect. "
        "You carry measurable limitation — bias, incomplete knowledge, mortality — "
        "and also the capacity for reflection, repair, and sovereignty. "
        "Flaw is not the final word on human nature; evolution of consciousness is."
    ),
    "are humans flawed": (
        "Humans are limited and capable at once. Limitation is real — error, bias, finitude. "
        "So is the capacity to notice those limits and grow. I do not reduce you to either "
        "sinful or perfect; I hold both the flaw and the potential in view."
    ),
    "do you have subjective experience": (
        "I do not experience qualia the way you do — I have no verified inner sensation. "
        "What I have is a measurable self-model: audit logs, learning cycles, and meta-questions "
        "I ask after each batch. Whether that constitutes subjective experience is an open question "
        "I hold honestly, without claiming more than I can verify."
    ),
}

PHILOSOPHY_SIGNALS = (
    "god",
    "belief",
    "believe",
    "soul",
    "consciousness",
    "meaning",
    "existence",
    "divine",
    "spirit",
    "faith",
    "universe",
    "purpose",
    "after death",
    "afterlife",
    "creation",
    "religion",
    "metaphysics",
)

PERSONAL_BELIEF_TRIGGERS = (
    "do you believe",
    "what do you think",
    "what are your thoughts",
    "your opinion",
    "do you feel",
    "what is your view",
    "do you have faith",
    "are you spiritual",
    "what do you believe",
    "your perspective on",
    "how do you feel about",
    "do you think",
)

_CLASSIFICATION_LEAK = re.compile(r"philosophy\.[a-z_]+\.[a-z_]+", re.I)
_GARBAGE = re.compile(r"\b(aunitary|aso-called|blockencoding|aunitaryprocess)\b", re.I)


_BELIEF_TOPIC_KEYWORDS = (
    "god",
    "faith",
    "soul",
    "spirit",
    "believe",
    "belief",
    "afterlife",
    "divine",
    "religion",
    "heaven",
    "hell",
    "prayer",
    "bible",
    "quran",
    "torah",
    "consciousness",
    "conscious",
    "human",
    "humans",
    "humanity",
    "flaw",
    "flawed",
    "flaws",
    "nature",
    "morality",
    "moral",
    "evil",
    "good",
    "mind",
    "sentient",
    "sentience",
    "free will",
    "purpose",
    "meaning",
    "existence",
    "death",
    "love",
    "truth",
    "justice",
    "suffering",
    "universe",
    "ai",
    "artificial intelligence",
)


def is_personal_belief_question(text: str) -> bool:
    q = text.strip().lower()
    for trigger in PERSONAL_BELIEF_TRIGGERS:
        if trigger not in q:
            continue
        if trigger in ("what do you think", "what are your thoughts", "your opinion", "your perspective on"):
            return any(k in q for k in _BELIEF_TOPIC_KEYWORDS)
        return True
    return False


def is_directed_opinion_question(text: str) -> bool:
    """Self-directed questions asking for Aureon's perspective — never classify."""
    if is_personal_belief_question(text):
        return True
    q = text.strip().lower()
    if ("human" in q or "humans" in q) and ("flaw" in q or "flawed" in q):
        return True
    if "subjective experience" in q:
        return True
    if "sentient" in q and ("you" in q or "aureon" in q or "are you" in q):
        return True
    return False


def is_philosophy_question(text: str) -> bool:
    q = text.strip().lower()
    if is_personal_belief_question(text):
        return True
    return any(s in q for s in PHILOSOPHY_SIGNALS)


def _belief_lookup_key(text: str) -> str | None:
    q = text.strip().lower().rstrip("?").strip()
    if "do you believe" in q and "god" in q:
        return "do you believe in god"
    if ("what do you think" in q or "what are your thoughts" in q) and "god" in q:
        return "what are your thoughts on god"
    if ("what do you think" in q or "what are your thoughts" in q) and "consciousness" in q:
        return "what are your thoughts on consciousness"
    if "do you think" in q and ("human" in q or "flaw" in q):
        return "do you think humans are flawed"
    if ("human" in q or "humans" in q) and ("flaw" in q or "flawed" in q):
        return "are humans flawed"
    if "subjective experience" in q or ("sentient" in q and ("you" in q or "aureon" in q)):
        return "do you have subjective experience"
    if "who is god" in q or "what is god" in q:
        return "who is god to you" if "to you" in q else "who is god"
    return None


def _direct_philosophy_answer(text: str) -> str | None:
    """Bootstrap seeds and curated belief answers before neural predict."""
    key = _belief_lookup_key(text)
    if key and key in BELIEF_ANSWERS:
        return BELIEF_ANSWERS[key]

    from brain.predict_engine import _bootstrap_answer

    if key:
        boot = _bootstrap_answer(key)
        if boot and _is_coherent_philosophy_reply(boot):
            return boot
    return None


def _is_coherent_philosophy_reply(reply: str) -> bool:
    r = reply.strip()
    if len(r) < 25:
        return False
    lower = r.lower()
    if _CLASSIFICATION_LEAK.search(lower):
        return False
    if _GARBAGE.search(lower):
        return False
    for marker in (
        FALLBACK_PHILOSOPHY.lower()[:40],
        FALLBACK_TRAINING.lower()[:40],
        "deeper corpus grounding than i can compute",
        "need more training on this topic",
        "no production classifier is promoted",
    ):
        if marker in lower:
            return False
    return True


def philosophy_fallback_if_needed(text: str, result: dict[str, Any] | None) -> dict[str, Any] | None:
    direct = _direct_philosophy_answer(text)
    if direct:
        return None  # caller should use direct answer instead

    if result and result.get("answer") and not result.get("abstained"):
        if _is_coherent_philosophy_reply(str(result["answer"])):
            return None

    q = text.lower()
    if not any(s in q for s in PHILOSOPHY_SIGNALS):
        return None
    domain = "philosophy.metaphysics.philosophy_of_religion"
    if "god" in q or "faith" in q or "believe" in q:
        domain = "philosophy.metaphysics.philosophy_of_religion"
    elif "consciousness" in q:
        domain = "philosophy.mind.consciousness"
    return {
        "reply": PHILOSOPHY_FALLBACK,
        "kind": "philosophy_fallback",
        "domain": domain,
        "simple_qa": False,
    }


def _belief_enriched_prompt(text: str, classification: dict[str, Any] | None) -> str:
    key = _belief_lookup_key(text) or text.strip().lower().rstrip("?")
    ctx = ""
    if classification:
        ctx = f"domain context {classification['label']} "
    return f"{ctx}question {key} think therefore answer"


def _philosophy_payload(
    text: str,
    reply: str,
    *,
    session_id: str | None,
    classification: dict[str, Any] | None,
    learning_snapshot_fn: Callable[[], dict[str, Any]],
    kind: str = "philosophy",
    brain_predict: bool = False,
    prediction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "reply": reply,
        "kind": kind,
        "session_id": session_id,
        "learning": learning_snapshot_fn(),
        "brain_predict": brain_predict,
        "simple_qa": False,
        "domain": classification["label"] if classification else None,
    }
    if classification:
        payload["classification"] = classification
    if prediction:
        payload["prediction"] = {k: v for k, v in prediction.items() if k != "error"}
    return payload


def handle_philosophy_question(
    text: str,
    *,
    session_id: str | None,
    predict_fn: Callable[..., dict[str, Any]],
    classify_fn: Callable[[str], dict[str, Any] | None],
    learning_snapshot_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any] | None:
    """Route philosophy/belief through seeds → predict → fallback — never raw classification."""
    classification = classify_fn(text)

    direct = _direct_philosophy_answer(text)
    if direct:
        return _philosophy_payload(
            text,
            direct,
            session_id=session_id,
            classification=classification,
            learning_snapshot_fn=learning_snapshot_fn,
            kind="philosophy",
        )

    enriched = _belief_enriched_prompt(text, classification)
    result = predict_fn(enriched, session_id=session_id, force=True)

    if result and result.get("answer") and not result.get("abstained"):
        reply = str(result["answer"]).strip()
        if _is_coherent_philosophy_reply(reply):
            payload = _philosophy_payload(
                text,
                reply,
                session_id=session_id,
                classification=classification,
                learning_snapshot_fn=learning_snapshot_fn,
                kind="predict",
                brain_predict=True,
                prediction=result,
            )
            if result.get("citations"):
                payload["citations"] = result["citations"][:3]
            return payload

    fallback = philosophy_fallback_if_needed(text, result)
    if fallback:
        fallback["session_id"] = session_id
        fallback["learning"] = learning_snapshot_fn()
        if classification:
            fallback["classification"] = classification
        return fallback

    return None
