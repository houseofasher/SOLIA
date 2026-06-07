"""OmniSpider seed augmentation mirrors trusted-site search URLs."""

from __future__ import annotations

from brain.omnispider_bridge import augment_seeds_for_question


def test_augment_seeds_adds_britannica_search():
    seeds = ["https://www.britannica.com/science/physics"]
    out = augment_seeds_for_question(seeds, "What is quantum mechanics?")
    joined = " ".join(out)
    assert "britannica.com/search" in joined
    assert "quantum" in joined.lower()
