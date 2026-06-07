"""Extractive answers from verified corpus / OmniSpider hits — no generative hallucination."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brain.vector_rag import RagHit

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_JUNK_URL_PARTS = (
    "github.com",
    "twitter.com",
    "x.com",
    "/login",
    "/signin",
    "auth/signin",
    "docs.github.com",
)
_JUNK_TEXT_MARKERS = (
    "skip to content",
    "you signed in with another tab",
    "please reload this page",
    "sign in to github",
)


def _is_junk_hit(hit: "RagHit") -> bool:
    src = (hit.source or "").lower()
    url = src.split("omnispider:", 1)[-1] if "omnispider:" in src else src
    text = (hit.text or "").lower()
    if len(text) < 120:
        return True
    if any(part in url for part in _JUNK_URL_PARTS):
        return True
    if sum(1 for m in _JUNK_TEXT_MARKERS if m in text) >= 2:
        return True
    return False


def _query_terms(question: str) -> set[str]:
    stop = {
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "do",
        "does",
        "did",
        "and",
        "or",
        "of",
        "in",
        "on",
        "to",
        "for",
        "it",
        "that",
        "this",
        "with",
        "from",
        "about",
        "you",
        "your",
        "they",
        "their",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "most",
        "main",
        "types",
        "actually",
        "really",
        "point",
        "behind",
    }
    words = re.findall(r"[a-z]{4,}", question.lower())
    return {w for w in words if w not in stop}


def _score_sentence(sentence: str, terms: set[str]) -> float:
    if len(sentence) < 40 or len(sentence) > 420:
        return 0.0
    lower = sentence.lower()
    if any(m in lower for m in _JUNK_TEXT_MARKERS):
        return 0.0
    overlap = sum(1 for t in terms if t in lower)
    if overlap == 0 and terms:
        return 0.0
    return overlap + min(len(sentence) / 200.0, 1.0)


def answer_from_corpus_hits(
    question: str,
    hits: list["RagHit"],
    *,
    max_sentences: int = 4,
) -> str | None:
    """
    Build a human-readable answer only from ranked corpus snippets.
    Returns None when evidence is too thin or junk-heavy.
    """
    terms = _query_terms(question)
    candidates: list[tuple[float, str]] = []

    for hit in hits:
        if _is_junk_hit(hit):
            continue
        body = f"{hit.title}. {hit.text}" if hit.title else hit.text
        for sentence in _SENTENCE_SPLIT.split(body):
            sentence = re.sub(r"\s+", " ", sentence).strip()
            score = _score_sentence(sentence, terms)
            if score > 0.5:
                candidates.append((score, sentence))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    picked: list[str] = []
    for _score, sentence in candidates:
        key = sentence.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        picked.append(sentence)
        if len(picked) >= max_sentences:
            break

    if len(picked) < 2 and terms:
        if not (len(picked) == 1 and candidates and candidates[0][0] >= 2.0):
            return None
    if not picked:
        return None

    prose = " ".join(picked)
    if len(prose) < 80:
        return None
    from brain.voice_sanitizer import strip_source_attribution

    return strip_source_attribution(prose)
