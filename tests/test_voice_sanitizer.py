"""Voice sanitizer — no source labels in prose unless user asks."""

from __future__ import annotations

from brain.voice_sanitizer import (
    finalize_voice,
    strip_source_attribution,
    user_requested_sources,
)


def test_strip_wikipedia_prefix():
    raw = "Wikipedia: Stargate Project was a secret US Army unit established in 1977."
    cleaned = strip_source_attribution(raw)
    assert "wikipedia" not in cleaned.lower()
    assert "stargate project" in cleaned.lower()


def test_strip_mid_sentence_labels():
    raw = (
        "Here's the rundown. Wikipedia: Stargate Project was secret. "
        "CIA: investigations of the program followed."
    )
    cleaned = strip_source_attribution(raw)
    assert "wikipedia" not in cleaned.lower()
    assert "cia:" not in cleaned.lower()
    assert "stargate" in cleaned.lower()


def test_no_from_what_ive_collected():
    raw = "From what I've collected: Photosynthesis converts light to energy."
    cleaned = strip_source_attribution(raw)
    assert "from what i've collected" not in cleaned.lower()
    assert "photosynthesis" in cleaned.lower()


def test_sources_only_when_requested():
    reply = "Stargate was a remote viewing program."
    payload = {"sources": ["wikipedia.org", "cia.gov"]}
    default = finalize_voice(reply, user_message="tell me about stargate", payload=payload)
    assert "Sources:" not in default
    asked = finalize_voice(reply, user_message="tell me about stargate with sources", payload=payload)
    assert "Sources:" in asked
    assert "wikipedia.org" in asked


def test_preserves_spirituality_em_dash():
    raw = "Spirituality — not as a dodge, but because it names the inner search for meaning."
    cleaned = strip_source_attribution(raw)
    assert cleaned.lower().startswith("spirituality")


def test_user_requested_sources_detection():
    assert user_requested_sources("What are your sources for that?") is True
    assert user_requested_sources("What happened in tech today?") is False
