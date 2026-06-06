"""Response adequacy audit — generic logic, not per-question patches.

Layer 6 self-correction for every chat output: detect when the reply fails to
answer the question and reroute through a better handler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from brain.system_messages import (
    FALLBACK_CORPUS,
    FALLBACK_PHILOSOPHY,
    FALLBACK_TIMEOUT,
    FALLBACK_TRAINING,
)

_CLASSIFICATION_LEAK_RE = re.compile(r"^[a-z_]+\.[a-z_]+\.[a-z_]+", re.I)
_TAXONOMY_ARROW_RE = re.compile(r"\b[a-z_]+\s*→\s*[A-Za-z]", re.I)
_FORUM_DATE_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{4}\b",
    re.I,
)
_FORUM_QA_RE = re.compile(r"\?\:\s|\?\s*[·•]\s*", re.I)
_DISAMBIG_OPTION_RE = re.compile(r"^\d+\.\s+\S+\s*→", re.M)

_STOPWORDS = frozenset(
    {
        "what",
        "when",
        "where",
        "which",
        "would",
        "could",
        "should",
        "about",
        "there",
        "their",
        "they",
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "were",
        "your",
        "you",
        "the",
        "and",
        "for",
        "are",
        "how",
        "why",
        "who",
        "did",
        "does",
        "into",
        "than",
        "then",
        "some",
        "like",
        "just",
        "also",
        "tell",
        "explain",
        "describe",
        "give",
        "make",
        "need",
        "want",
        "know",
        "best",
        "good",
        "much",
        "many",
        "most",
        "more",
        "very",
        "really",
        "actually",
        "thing",
        "things",
        "something",
        "anything",
    }
)

_DIRECTED_CHOICE_MARKERS = (
    "if you had to",
    "would you choose",
    "which would you",
    "what would you choose",
    "what would you pick",
    "if you could only",
    "forced to choose",
    "would you rather",
    "would you prefer",
    "pick one",
    "choose one",
)

_LIVE_MARKERS = (
    "today",
    "right now",
    "currently",
    "latest",
    "this week",
    "happened",
    "breaking",
    "news",
    "price of",
    "stock",
)

_HOW_TO_MARKERS = ("how do i", "how can i", "how to", "steps to", "way to")

_INQUIRY_MARKERS = (
    "tell me about",
    "can you tell me about",
    "what is the history of",
    "history of the",
    "history about the",
    "history about",
    "explain the",
    "what was the",
    "what were the",
)

_SPECIFIC_TOPIC_HINTS = (
    "project",
    "program",
    "operation",
    "scandal",
    "treaty",
    "mission",
    "agency",
    "experiment",
)


class QuestionIntent(str, Enum):
    DIRECTED_PERSONAL = "directed_personal"
    LIVE = "live"
    HOW_TO = "how_to"
    NAMED_ENTITY = "named_entity"
    PHILOSOPHY = "philosophy"
    HISTORICAL = "historical"
    FACTUAL = "factual"
    GENERAL = "general"


class RecoveryRoute(str, Enum):
    DIRECTED_REFLECTION = "directed_reflection"
    LIVE_SEARCH = "live_search"
    DEEP_CONCEPT = "deep_concept"
    NAMED_ENTITY = "named_entity"
    CODE = "code"
    PREDICT = "predict"
    NONE = "none"


@dataclass
class AuditResult:
    adequate: bool
    reasons: list[str] = field(default_factory=list)
    intent: QuestionIntent = QuestionIntent.GENERAL
    recovery: RecoveryRoute = RecoveryRoute.NONE


def is_directed_choice_question(text: str) -> bool:
    q = text.strip().lower()
    if any(m in q for m in _DIRECTED_CHOICE_MARKERS):
        return "you" in q or "your" in q or "aureon" in q or "solia" in q
    if re.search(r"what .{0,40} would you (choose|pick|select)", q):
        return True
    if re.search(r"which .{0,40} would you (choose|pick|select)", q):
        return True
    return False


def is_specific_topic_inquiry(text: str) -> bool:
    """Detect requests about a named project, program, or proper-noun topic — not broad domains."""
    q = text.strip()
    q_lower = q.lower()
    if not any(m in q_lower for m in _INQUIRY_MARKERS):
        return False
    if re.search(r"\b[A-Z]{2,}\b", q):
        return True
    words = q.split()
    proper = [w for w in words if w[0].isupper() and len(w) > 1 and w.isalpha()]
    if len(proper) >= 2:
        return True
    if proper and any(h in q_lower for h in _SPECIFIC_TOPIC_HINTS):
        return True
    return bool(proper) and "history" in q_lower


def infer_question_intent(question: str) -> QuestionIntent:
    q = question.strip().lower()
    if is_directed_choice_question(question):
        return QuestionIntent.DIRECTED_PERSONAL
    if is_specific_topic_inquiry(question):
        return QuestionIntent.HISTORICAL
    if any(m in q for m in _HOW_TO_MARKERS):
        return QuestionIntent.HOW_TO
    if any(m in q for m in _LIVE_MARKERS):
        return QuestionIntent.LIVE
    if q.startswith(("who is", "who was", "who were")) or "tell me about" in q:
        return QuestionIntent.NAMED_ENTITY
    if any(s in q for s in ("god", "soul", "consciousness", "meaning of life", "afterlife", "belief")):
        return QuestionIntent.PHILOSOPHY
    if any(s in q for s in ("when did", "history of", "who invented", "who discovered", "ancient", "century")):
        return QuestionIntent.HISTORICAL
    if q.startswith(("what is", "what are", "why is", "why do", "why does", "explain", "define")):
        return QuestionIntent.FACTUAL
    return QuestionIntent.GENERAL


def infer_recovery_route(
    question: str,
    payload: dict[str, Any],
    *,
    reasons: list[str],
) -> RecoveryRoute:
    intent = infer_question_intent(question)
    kind = str(payload.get("kind", ""))

    if "directed_missed" in reasons or intent in (
        QuestionIntent.DIRECTED_PERSONAL,
        QuestionIntent.PHILOSOPHY,
    ):
        return RecoveryRoute.DIRECTED_REFLECTION
    if "ciper_decompose_missed" in reasons or (
        is_specific_topic_inquiry(question)
        and kind in ("chat", "predict")
        and payload.get("ciper", {}).get("mode") == "decompose"
    ):
        return RecoveryRoute.DEEP_CONCEPT
    if is_specific_topic_inquiry(question) and kind not in (
        "named_entity",
        "search_opinion",
        "deep_concept",
        "deep_concept_search",
    ):
        return RecoveryRoute.DEEP_CONCEPT
    if "live_missed" in reasons or (
        intent == QuestionIntent.LIVE and kind not in ("search_opinion", "deep_concept_search")
    ):
        return RecoveryRoute.LIVE_SEARCH
    if intent == QuestionIntent.NAMED_ENTITY and kind not in ("named_entity", "search_opinion"):
        return RecoveryRoute.NAMED_ENTITY
    if intent == QuestionIntent.HOW_TO and kind != "code":
        if any(t in question.lower() for t in ("python", "code", "function", "script", "javascript")):
            return RecoveryRoute.CODE
        return RecoveryRoute.DEEP_CONCEPT
    if intent in (QuestionIntent.FACTUAL, QuestionIntent.HISTORICAL):
        return RecoveryRoute.DEEP_CONCEPT
    if "forum_garbage" in reasons or "off_topic" in reasons or "weak_fallback" in reasons:
        if intent == QuestionIntent.LIVE:
            return RecoveryRoute.LIVE_SEARCH
        if intent in (QuestionIntent.DIRECTED_PERSONAL, QuestionIntent.PHILOSOPHY):
            return RecoveryRoute.DIRECTED_REFLECTION
        if intent == QuestionIntent.HOW_TO:
            return RecoveryRoute.DEEP_CONCEPT
        return RecoveryRoute.DEEP_CONCEPT
    return RecoveryRoute.PREDICT


def _significant_terms(question: str) -> set[str]:
    words = re.findall(r"[a-z]{4,}", question.lower())
    return {w for w in words if w not in _STOPWORDS}


def is_forum_garbage(reply: str) -> bool:
    r = reply.strip()
    if len(r) < 40:
        return False
    hits = 0
    if _FORUM_DATE_RE.search(r):
        hits += 1
    if _FORUM_QA_RE.search(r):
        hits += 1
    if r.lower().count("?:") >= 2:
        hits += 1
    if any(s in r.lower() for s in ("facebook", "reddit", "quora", "yahoo answers")):
        hits += 1
    if len(re.findall(r"\?\:", r)) >= 2:
        hits += 1
    return hits >= 2


def is_system_fallback(reply: str) -> bool:
    text = reply.strip().lower()
    if not text:
        return True
    for marker in (
        FALLBACK_CORPUS.lower(),
        FALLBACK_TIMEOUT.lower(),
        FALLBACK_TRAINING.lower(),
        FALLBACK_PHILOSOPHY.lower()[:50],
        "deeper corpus grounding than i can compute",
        "hit my compute time limit",
        "need more training on this topic",
        "i mapped your question to **",
        "no production classifier is promoted",
    ):
        if marker in text:
            return True
    return False


def answer_addresses_question(question: str, reply: str) -> bool:
    terms = _significant_terms(question)
    if not terms:
        return len(reply.strip()) >= 20
    reply_lower = reply.lower()
    hits = sum(1 for t in terms if t in reply_lower)
    anchor = max(terms, key=len)
    if len(anchor) >= 6 and anchor in reply_lower and hits >= 1:
        return True
    minimum = 1 if len(terms) <= 3 else max(2, int(len(terms) * 0.25))
    return hits >= minimum


def audit_response(question: str, reply: str, payload: dict[str, Any]) -> AuditResult:
    """Return whether the reply adequately answers the question."""
    reasons: list[str] = []
    intent = infer_question_intent(question)
    r = reply.strip()
    kind = str(payload.get("kind", ""))

    if not r:
        reasons.append("empty")

    if _CLASSIFICATION_LEAK_RE.match(r) or _TAXONOMY_ARROW_RE.search(r):
        reasons.append("taxonomy_leak")

    if is_system_fallback(r) and kind not in ("philosophy_fallback", "reflection"):
        reasons.append("weak_fallback")

    if is_forum_garbage(r):
        reasons.append("forum_garbage")

    if _DISAMBIG_OPTION_RE.search(r) and "did you mean" in r.lower():
        reasons.append("disambiguation")

    if kind == "predict" and payload.get("classification"):
        conf = float(payload.get("classification", {}).get("confidence", 0) or 0)
        if conf < 0.35 and not answer_addresses_question(question, r):
            reasons.append("off_topic")

    if intent == QuestionIntent.DIRECTED_PERSONAL and kind not in (
        "reflection",
        "identity",
        "philosophy",
    ):
        reasons.append("directed_missed")

    ciper = payload.get("ciper") or {}
    if ciper.get("mode") == "decompose" and is_specific_topic_inquiry(question):
        reasons.append("ciper_decompose_missed")

    if intent == QuestionIntent.PHILOSOPHY and kind in (
        "reflection",
        "philosophy",
        "philosophy_fallback",
        "predict",
    ) and not is_forum_garbage(r) and not is_system_fallback(r):
        pass  # acceptable philosophy path
    elif intent == QuestionIntent.LIVE and kind not in (
        "search_opinion",
        "deep_concept_search",
    ):
        if not answer_addresses_question(question, r):
            reasons.append("live_missed")

    if len(r) < 28 and not payload.get("simple_qa") and kind not in ("chat",):
        if not payload.get("deterministic"):
            reasons.append("too_short")

    if not answer_addresses_question(question, r) and kind in ("predict", "classified"):
        if "off_topic" not in reasons:
            reasons.append("off_topic")

    recovery = RecoveryRoute.NONE
    if reasons:
        recovery = infer_recovery_route(question, payload, reasons=reasons)

    return AuditResult(
        adequate=not reasons,
        reasons=reasons,
        intent=intent,
        recovery=recovery,
    )


def try_recover_response(
    question: str,
    payload: dict[str, Any],
    *,
    session_id: str | None,
    recover_handlers: dict[RecoveryRoute, Callable[..., dict[str, Any] | None]],
) -> dict[str, Any] | None:
    """Attempt one recovery pass when audit fails."""
    reply = str(payload.get("reply", ""))
    audit = audit_response(question, reply, payload)
    if audit.adequate:
        return None

    handler = recover_handlers.get(audit.recovery)
    if not handler or audit.recovery == RecoveryRoute.NONE:
        return None

    recovered = handler(question, session_id=session_id, prior=payload, audit=audit)
    if not recovered:
        return None

    new_reply = str(recovered.get("reply", "")).strip()
    if not new_reply or new_reply == reply:
        return None

    reaudit = audit_response(question, new_reply, recovered)
    if reaudit.adequate:
        pass
    elif is_system_fallback(new_reply) or is_forum_garbage(new_reply):
        return None
    elif len(reaudit.reasons) >= len(audit.reasons):
        return None

    recovered["quality_recovered"] = True
    recovered["quality_audit"] = {
        "prior_reasons": audit.reasons,
        "recovery": audit.recovery.value,
        "intent": audit.intent.value,
    }
    return recovered
