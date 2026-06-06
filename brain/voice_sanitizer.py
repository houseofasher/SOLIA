"""Voice sanitizer — speak with confidence; cite only when the user asks."""

from __future__ import annotations

import re
from typing import Any

_SOURCES_BLOCK_RE = re.compile(r"\n\nSources:.*$", re.DOTALL | re.IGNORECASE)

_SOURCE_REQUEST_MARKERS = (
    "source",
    "sources",
    "cite",
    "citation",
    "citations",
    "where did you get",
    "where did you hear",
    "where did you read",
    "give me a link",
    "show me a link",
    "link to",
    "reference",
    "references",
    "prove it",
    "show proof",
    "show your sources",
    "what url",
    "which site",
)

_KNOWN_LABELS = (
    "wikipedia",
    "reuters",
    "cnn",
    "bbc",
    "cia",
    "noaa",
    "google",
    "ibm",
    "techcrunch",
    "reddit",
    "facebook",
    "quora",
    "medium",
    "yahoo",
    "investopedia",
    "cnbc",
    "wired",
    "nsa",
    "congress",
)

# Short org/site labels only — never strip normal prose em-dashes.
_SHORT_LABEL_RE = re.compile(
    r"(?:^|[.!?]\s+)"
    r"([A-Za-z][A-Za-z0-9 &'\-\.]{1,40}(?:\.{3})?)\s*[\-–—:]\s*",
    re.IGNORECASE,
)


def _is_source_label(label: str) -> bool:
    low = label.lower().strip().rstrip(".:")
    if low in _KNOWN_LABELS:
        return True
    if low.endswith("..."):
        return True
    words = low.split()
    if len(words) > 4:
        return False
    if any(t in low for t in ("news", "times", "journal", "chronicle", "post", "herald", "foia", ".gov", ".com")):
        return True
    return False

_LEADING_BOILERPLATE_RE = re.compile(
    r"^(?:"
    r"From what I['']ve collected:\s*"
    r"|From my trained corpus:\s*"
    r"|According to [^,.:!?\n]{3,80}[,:]\s*"
    r"|Based on \d+ sources[^.]*\.\s*"
    r")",
    re.IGNORECASE,
)


def user_requested_sources(message: str) -> bool:
    q = (message or "").strip().lower()
    return any(m in q for m in _SOURCE_REQUEST_MARKERS)


def strip_source_attribution(text: str) -> str:
    """Remove source/site labels from prose — answer stands on its own."""
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned

    cleaned = _SOURCES_BLOCK_RE.sub("", cleaned)
    cleaned = _LEADING_BOILERPLATE_RE.sub("", cleaned)
    cleaned = re.sub(
        r"(?i)(?:^|[.!?]\s+)[A-Za-z0-9][A-Za-z0-9 \-\']{0,50}\([^)]+\)\s*:\s*",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"(?i)\b(?:cia|nsa|fbi|dod)\s*:\s*", "", cleaned)
    cleaned = re.sub(r"Missing:\s*[^|]+\|\s*Show results with:[^.]*\.?\s*", "", cleaned, flags=re.I)

    for label in _KNOWN_LABELS:
        cleaned = re.sub(
            rf"(?i)(?:^|[.!?]\s+){re.escape(label)}\s*[\-–—:]\s*",
            " ",
            cleaned,
        )

    for _ in range(6):
        match = _SHORT_LABEL_RE.search(cleaned)
        if not match:
            break
        label = match.group(1)
        if not _is_source_label(label):
            break
        cleaned = cleaned[: match.start()] + " " + cleaned[match.end() :]

    cleaned = re.sub(r"^\s+[\-–—:]\s*", "", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"(?<=[.!?])\s+(?=[.!?])", " ", cleaned)
    return cleaned


def format_sources_appendix(reply: str, payload: dict[str, Any]) -> str:
    """When the user asked for sources, append a compact list from payload metadata."""
    sources: list[str] = []
    for key in ("sources",):
        raw = payload.get(key) or []
        if isinstance(raw, list):
            sources.extend(str(s).strip() for s in raw if str(s).strip())
    citations = payload.get("citations") or []
    if isinstance(citations, list):
        for cite in citations:
            if isinstance(cite, dict):
                src = str(cite.get("source") or cite.get("url") or "").strip()
                if src:
                    sources.append(src)
            elif cite:
                sources.append(str(cite).strip())

    unique = list(dict.fromkeys(sources))[:8]
    if not unique:
        return reply
    return f"{reply.rstrip()}\n\nSources: {', '.join(unique)}"


def finalize_voice(reply: str, *, user_message: str, payload: dict[str, Any]) -> str:
    """Apply voice policy: confident prose by default; sources only on request."""
    if user_requested_sources(user_message):
        cleaned = strip_source_attribution(reply)
        return format_sources_appendix(cleaned, payload)
    return strip_source_attribution(reply)
