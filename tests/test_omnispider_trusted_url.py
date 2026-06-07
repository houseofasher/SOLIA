"""Trusted crawl URL gate — web data only from whitelist hosts."""

from __future__ import annotations

from brain.omnispider_bridge import _is_trusted_crawl_url


def test_blocks_github_drift():
    assert _is_trusted_crawl_url("https://github.com/foo/bar", ["britannica.com"]) is False


def test_allows_britannica_on_whitelist():
    assert _is_trusted_crawl_url("https://www.britannica.com/topic/algorithm", ["britannica.com"]) is True
