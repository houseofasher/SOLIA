"""Simple Question, Simple Answer — core Aureon response policy."""

from __future__ import annotations

import re

SIMPLE_QA_RULE = "Simple Question, Simple Answer"

QUESTION_MAX_WORDS = 15
QUESTION_MAX_CHARS = 120
ANSWER_MAX_CHAT = 140
ANSWER_MAX_INQUIRY_PRESCHOOL = 80
ANSWER_MAX_INQUIRY_DEFAULT = 120

_SIMPLE_STARTERS = (
    "what ",
    "who ",
    "when ",
    "where ",
    "why ",
    "how ",
    "is ",
    "are ",
    "do ",
    "does ",
    "can ",
    "define ",
)


def is_simple_question(text: str) -> bool:
    """True when the user asks a direct, short question."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned or cleaned.startswith("/"):
        return False
    if len(cleaned) > QUESTION_MAX_CHARS:
        return False
    if len(cleaned.split()) > QUESTION_MAX_WORDS:
        return False
    lower = cleaned.lower()
    if "?" in cleaned:
        return True
    if len(cleaned.split()) <= 6:
        return True
    return any(lower.startswith(starter) for starter in _SIMPLE_STARTERS)


def to_simple_answer(text: str, *, max_len: int = ANSWER_MAX_CHAT) -> str:
    """One short sentence — no paragraphs, no boilerplate."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return "No answer yet."

    for sep in (". ", "? ", "! ", " · ", "\n"):
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[0].strip()
            break

    cleaned = cleaned.strip("\"'«»")
    if len(cleaned) > max_len:
        cut = cleaned[:max_len].rsplit(" ", 1)[0]
        cleaned = (cut or cleaned[:max_len]).rstrip(".,;:")
    if cleaned and cleaned[-1] not in ".?!" and not re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
        cleaned += "."
    return cleaned
