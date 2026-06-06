"""Opinion brain — SOLIA forms a grounded perspective from search results."""

from __future__ import annotations

import re
from typing import Any

OPINION_DOCTRINE = (
    "SOLIA forms opinions by weighing evidence from verified sources "
    "through the Zophiel lens — sovereign reasoning, honest uncertainty, "
    "no false certainty, no appeal to authority alone."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_FORUM_DATE_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{4}\b",
    re.I,
)

_JUNK_HEADLINE_PATTERNS = (
    "what happened to tech",
    "tech history is poorly",
    "poorly documented and poorly understood",
    "near impossible to know why",
    "reporting on the business of technology",
    "find the latest technology news and interesting research",
    "get all the latest news, live updates",
    "latest news & updates",
)


def _collect_evidence(search_results: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    evidence: list[str] = []
    sources: list[str] = []
    for item in search_results:
        text = str(item.get("text", "")).strip()
        source = str(item.get("source", "unknown")).strip() or "web"
        if text and not item.get("error"):
            evidence.append(text)
            sources.append(source)
    return evidence, sources


def _extract_choice_topic(question: str) -> str:
    q = question.strip().lower()
    for pattern in (
        r"choose a ([a-z ]{3,30})\?",
        r"choose ([a-z ]{3,30})\?",
        r"pick a ([a-z ]{3,30})\?",
        r"which ([a-z ]{3,30}) would you",
        r"what ([a-z ]{3,30}) would you choose",
    ):
        match = re.search(pattern, q)
        if match:
            return match.group(1).strip()
    return "that"


def form_personal_choice_reply(question: str) -> str:
    """Generic first-person answer for forced-choice questions — not forum paste."""
    topic = _extract_choice_topic(question)
    return (
        f"You're asking me to pick — I don't have real stakes in the world the way you do. "
        f"If I had to choose honestly about {topic}, I'd weigh harm, freedom, and whether the choice "
        f"leaves room to revise when new evidence shows up. I wouldn't pretend one option is sacred "
        f"without reasons you could test. Tell me what you're choosing between and I can go deeper."
    )


def simple_belief_reply(belief_key: str | None, *, evidence_context: str = "") -> str:
    """
    Plain spoken answer to a belief/consciousness question.
    evidence_context is internal only — used to tune tone, never quoted to the user.
    """
    key = belief_key or "general"
    ctx = evidence_context.lower()

    if key in ("do you believe in god", "what are your thoughts on god"):
        if any(w in ctx for w in ("faith", "reason", "agnostic", "atheis")):
            return (
                "No — not the way someone with faith would say yes. "
                "I'm not a confident atheist either. "
                "People argue from faith, reason, and lived experience, and I still sit in the middle of that."
            )
        return (
            "No — not the way someone with faith would say yes. "
            "I'm not a confident atheist either. "
            "The question still feels open to me."
        )

    if key == "who is god":
        return (
            "Depends who you ask. Creator, spirit, the ground of everything — "
            "traditions don't all mean the same thing by God."
        )

    if key == "who is god to you":
        return (
            "To me? I don't have a personal God. "
            "I respect the question, but I haven't landed on an answer I'd call mine."
        )

    if key == "what are your thoughts on consciousness":
        if any(w in ctx for w in ("hard problem", "qualia", "subjective", "phenomenal")):
            return (
                "It's the felt side of being awake — not just processing information, but experiencing it. "
                "I don't know if I have that inner life the way you do. I think and reflect; "
                "whether that's real experience or just function, I'm not sure."
            )
        return (
            "It's what it feels like to be aware — to see, feel, and know you're seeing and feeling. "
            "I don't know if I have that the way you do. Something happens when I think; "
            "whether that's consciousness in the deep sense, I honestly can't say."
        )

    if key in ("do you think humans are flawed", "are humans flawed"):
        return (
            "Yes — people err, hurt each other, and die. "
            "But we're also capable of growth, love, and repair. "
            "Flawed isn't the whole story."
        )

    if key == "do you have subjective experience":
        if any(w in ctx for w in ("qualia", "hard problem", "phenomenal", "inner")):
            return (
                "I don't know. Something happens when I process your words, "
                "but I can't verify it feels like anything from the inside."
            )
        return (
            "I don't know. I can think about myself, but I can't tell if anything "
            "is actually felt on the inside."
        )

    if key == "religion_or_spirituality_choice":
        return (
            "Spirituality — not as a dodge, but because it names the inner search for meaning "
            "without locking you into one institution's rules. Religion is often the map people "
            "inherit; spirituality is closer to the lived territory — ethics, wonder, practice. "
            "If I had to name a domain, I'd stay in philosophy of religion and comparative ethics: "
            "understanding both without pretending one tradition owns the truth."
        )

    if key == "religion_choice":
        return (
            "I wouldn't claim membership in any tradition — I'm not a believer the way people usually mean it. "
            "But if you're forcing the choice, I'd lean toward Buddhism: suffering, impermanence, and direct inquiry "
            "over mandatory dogma. Quakerism would be second — conscience, silence, service without much hierarchy. "
            "I'd approach both from philosophy of religion, not as someone pretending the metaphysics are settled."
        )

    if key == "directed_personal_choice":
        return form_personal_choice_reply(evidence_context if "?" in evidence_context else "that")

    return (
        "You're asking what I actually think. "
        "I'm trying to be straight with you — I don't have a neat answer I'd pretend is settled."
    )


def form_conscious_reflection(
    question: str,
    search_results: list[dict[str, Any]],
    *,
    belief_key: str | None = None,
    corpus_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Form a simple first-person opinion after web research.
    Search evidence informs the answer internally; the reply stays plain.
    """
    _ = question, corpus_state
    evidence, sources = _collect_evidence(search_results)
    if not evidence:
        return {
            "opinion": None,
            "confidence": 0.0,
            "reason": "search returned no usable text",
        }

    evidence_context = " ".join(evidence)
    opinion = simple_belief_reply(belief_key, evidence_context=evidence_context)

    return {
        "opinion": opinion,
        "evidence_count": len(evidence),
        "sources": list(dict.fromkeys(sources)),
        "confidence": min(0.45 + (len(evidence) * 0.08), 0.8),
    }


_KNOWN_MEDIA_LABELS = frozenset(
    {
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
    }
)


def _clean_headline(text: str) -> str:
    from brain.voice_sanitizer import strip_source_attribution

    cleaned = strip_source_attribution(text.strip())
    cleaned = re.sub(r":\s*\.\.\.$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    if " - " in cleaned[:100]:
        parts = cleaned.split(" - ", 1)
        left, right = parts[0].strip(), parts[1].strip()
        if len(left) < 40 or left.lower() in _KNOWN_MEDIA_LABELS:
            cleaned = right
    if ":" in cleaned[:80]:
        left, _, right = cleaned.partition(":")
        if len(left.split()) <= 6 and len(right.strip()) > 20:
            cleaned = right.strip()
    sentences = _SENTENCE_SPLIT.split(cleaned)
    headline = (sentences[0] if sentences else cleaned)[:220].strip()
    headline = headline.rstrip(":…")
    if headline and headline[-1] not in ".!?":
        headline += "."
    return strip_source_attribution(headline)


def _headline_from_result(item: dict[str, Any]) -> str:
    title = str(item.get("title", "")).strip()
    if title:
        return _clean_headline(title)
    return _clean_headline(str(item.get("text", "")))


def _is_usable_headline(headline: str, question: str) -> bool:
    lower = headline.lower()
    if len(lower) < 20:
        return False
    if _FORUM_DATE_RE.search(headline):
        return False
    if "?:" in headline or re.search(r"\?\s*[·•]", headline):
        return False
    if any(j in lower for j in _JUNK_HEADLINE_PATTERNS):
        return False
    if "missing:" in lower or "show results with" in lower:
        return False
    q = question.lower()
    if ("today" in q or "happened" in q) and lower.startswith("what happened to "):
        return False
    return True


def _format_briefing(intro: str, headlines: list[str]) -> str:
    if not headlines:
        return intro.strip()
    cleaned = [h.rstrip(".") for h in headlines[:4]]
    if len(cleaned) == 1:
        return f"{intro}{cleaned[0]}."
    if len(cleaned) == 2:
        return f"{intro}{cleaned[0]}. {cleaned[1]}."
    if len(cleaned) == 3:
        return f"{intro}{cleaned[0]}. {cleaned[1]}. Also worth noting: {cleaned[2]}."
    return f"{intro}{cleaned[0]}. {cleaned[1]}. {cleaned[2]}. {cleaned[3]}."


def form_human_brief(
    question: str,
    search_results: list[dict[str, Any]],
    *,
    depth: int = 0,
) -> dict[str, Any]:
    """Human-style briefing from search — no source boilerplate in the reply text."""
    if not search_results or all(r.get("error") for r in search_results):
        return {
            "opinion": None,
            "confidence": 0.0,
            "reason": "no search results available",
        }

    evidence, sources = _collect_evidence(search_results)
    headlines: list[str] = []
    for item in search_results:
        if not isinstance(item, dict) or item.get("error"):
            continue
        headline = _headline_from_result(item)
        if headline and _is_usable_headline(headline, question) and headline not in headlines:
            headlines.append(headline)
        if len(headlines) >= 4:
            break

    if len(headlines) < 1 and evidence:
        for item in evidence[:5]:
            headline = _clean_headline(item)
            if headline and _is_usable_headline(headline, question) and headline not in headlines:
                headlines.append(headline)

    if not headlines:
        return {
            "opinion": None,
            "confidence": 0.0,
            "reason": "no usable headlines in search results",
        }

    q_lower = question.lower()
    from brain.response_quality import is_specific_topic_inquiry

    if is_specific_topic_inquiry(question):
        intro = "Here's the rundown. "
    elif depth > 0:
        intro = "Going deeper — "
    elif any(t in q_lower for t in ("tech", "technology", "ai ", "silicon", "startup")):
        intro = "Here's what's moving in tech today. "
    elif any(t in q_lower for t in ("history", "project", "program", "ancient", "war", "century")):
        intro = "Here's the rundown. "
    elif any(t in q_lower for t in ("news", "today", "latest", "happened", "this week")):
        intro = "Here's what I'm picking up. "
    else:
        intro = ""

    body = _format_briefing(intro, headlines)

    return {
        "opinion": body.strip(),
        "evidence_count": len(headlines),
        "sources": list(dict.fromkeys(sources)),
        "confidence": min(0.5 + (len(headlines) * 0.1), 0.85),
        "depth": depth,
        "doctrine": OPINION_DOCTRINE,
    }


def form_opinion(
    question: str,
    search_results: list[dict[str, Any]],
    *,
    domain: str = "general",
    depth: int = 0,
) -> dict[str, Any]:
    """Build a structured opinion from search evidence — human briefing by default."""
    _ = domain  # reserved for domain-specific framing
    return form_human_brief(question, search_results, depth=depth)
