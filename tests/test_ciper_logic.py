"""Ciper logic — Marie/Ciper decomposition and cross-domain research."""

from __future__ import annotations

from brain.ciper_logic import (
    ciper_research,
    cross_domain_hits,
    format_ciper_question,
    facets_for_subject,
)
from app.chat_service import chat


def test_blood_claim_decomposes():
    result = ciper_research("I can move blood")
    assert result is not None
    assert result.mode == "decompose"
    assert "blood type" in result.reply.lower() or "plasma" in result.reply.lower()
    assert "facet_decomposition" in result.agi_traits


def test_format_ciper_question():
    q = format_ciper_question(
        "blood",
        ["blood type (ABO/Rh)", "plasma / water fraction", "red blood cells", "iron / hemoglobin"],
    )
    assert q.startswith("What type of blood,")
    assert "the iron / hemoglobin" in q


def test_cross_domain_hits_learning():
    hits = cross_domain_hits("learning intelligence")
    domains = {h.domain for h in hits}
    assert len(hits) >= 1
    assert len(domains) >= 1


def test_facets_for_blood():
    hits = cross_domain_hits("blood")
    facets = facets_for_subject("blood", hits)
    assert "plasma" in facets[1].lower() or "blood type" in facets[0].lower()


def test_chat_blood_decompose():
    result = chat("I can move blood")
    assert result["kind"] == "chat"
    assert "ciper" in result
    assert result["ciper"]["mode"] == "decompose"


def test_chat_research_command():
    result = chat("/research blood")
    assert result["kind"] == "research"
    assert "ciper" in result
    assert result["ciper"]["facets"]
