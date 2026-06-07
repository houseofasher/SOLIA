"""Map user questions to OmniSpider whitelist domain keys — keywords beat fuzzy classifier."""

from __future__ import annotations

import re

# (keyword phrases, domain-seeds.yaml key) — most specific lists first.
_DOMAIN_HINTS: list[tuple[tuple[str, ...], str]] = [
    (
        (
            "machine learning",
            "deep learning",
            "neural network",
            "transformer",
            "supervised learning",
            "reinforcement learning",
            "papers with code",
        ),
        "artificial_intelligence",
    ),
    (
        (
            "roman empire",
            "world war",
            "cold war",
            "ancient rome",
            "medieval",
            "prehistoric",
            "historical",
            "fall of rome",
        ),
        "history",
    ),
    (
        (
            "quantum mechanics",
            "quantum",
            "particle physics",
            "relativity",
            "thermodynamics",
            "electromagnetism",
            "string theory",
        ),
        "physics",
    ),
    (
        (
            "human evolution",
            "natural selection",
            "genetics",
            "molecular biology",
            "cell biology",
            "ecosystem",
            "organism",
            "dna",
            "rna",
        ),
        "biology",
    ),
    (
        (
            "self-sabotage",
            "self sabotage",
            "psychology",
            "cognitive bias",
            "anxiety",
            "depression",
            "trauma",
            "motivation",
            "behavioral",
        ),
        "psychology",
    ),
    (
        (
            "inflation",
            "deflation",
            "monetary policy",
            "fiscal policy",
            "gdp",
            "macroeconomics",
            "microeconomics",
            "interest rate",
            "central bank",
        ),
        "economics",
    ),
    (("calculus", "algebra", "geometry", "topology", "theorem", "mathematic"), "mathematics"),
    (("philosophy", "ethics", "metaphysics", "epistemology"), "humanities"),
]

_KNOWN_SEED_KEYS = frozenset(
    {
        "physics",
        "history",
        "artificial_intelligence",
        "computer_science",
        "biology",
        "mathematics",
        "humanities",
        "psychology",
        "economics",
        "science_and_natural_philosophy",
        "default",
    }
)

# Classifier labels that should NOT drive crawl seeds (too often wrong).
_CLASSIFIER_BLOCKLIST = frozenset({"computer_science"})


def _keyword_domain(question: str) -> str | None:
    q = question.lower()
    best_domain: str | None = None
    best_score = 0
    for keywords, domain in _DOMAIN_HINTS:
        score = sum(1 for phrase in keywords if phrase in q)
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain if best_score > 0 else None


def _label_to_crawl_domain(label: str) -> str | None:
    parts = [p.strip().lower() for p in label.split(".") if p.strip()]
    if not parts:
        return None
    if parts[0] in _CLASSIFIER_BLOCKLIST and len(parts) == 1:
        return None
    for part in reversed(parts):
        if part in _KNOWN_SEED_KEYS:
            return part
    return parts[0] if parts[0] not in _CLASSIFIER_BLOCKLIST else None


def resolve_crawl_domain(question: str, classifier_label: str | None = None) -> str | None:
    """
    Resolve OmniSpider domain key for a question.
    Keyword hints override classifier when present.
    """
    hinted = _keyword_domain(question)
    if hinted:
        return hinted
    if classifier_label:
        mapped = _label_to_crawl_domain(classifier_label)
        if mapped:
            return mapped
    return None


def is_knowledge_question(text: str) -> bool:
    """True for factual / explanatory questions that should use corpus + crawl."""
    q = text.strip().lower()
    if len(q) < 12:
        return False
    if re.match(r"^\d+\s*[\+\-\*/]", q):
        return False
    starters = (
        "what ",
        "why ",
        "how ",
        "when ",
        "where ",
        "who ",
        "explain ",
        "describe ",
        "tell me about",
        "what are the",
        "what is the",
        "what were",
        "what was",
    )
    return any(q.startswith(s) for s in starters) or "?" in q
