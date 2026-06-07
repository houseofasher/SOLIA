"""OmniSpider bridge — live crawl of whitelisted domains when corpus is thin."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrawledDocument:
    text: str
    url: str
    title: str
    source: str = "omnispider"


def omnispider_enabled() -> bool:
    return os.environ.get("OMNISPIDER_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _api_base() -> str:
    return os.environ.get("OMNISPIDER_API_URL", "http://127.0.0.1:8080").rstrip("/")


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    token = os.environ.get("OMNISPIDER_AUTH_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _timeout_sec() -> float:
    try:
        return max(10.0, float(os.environ.get("OMNISPIDER_TIMEOUT_SEC", "120")))
    except ValueError:
        return 120.0


def _poll_interval_sec() -> float:
    try:
        return max(0.5, float(os.environ.get("OMNISPIDER_POLL_INTERVAL_SEC", "2")))
    except ValueError:
        return 2.0


def _max_pages() -> int:
    try:
        return max(5, min(int(os.environ.get("OMNISPIDER_MAX_PAGES", "25")), 200))
    except ValueError:
        return 25


def _max_depth() -> int:
    try:
        return max(1, min(int(os.environ.get("OMNISPIDER_MAX_DEPTH", "2")), 5))
    except ValueError:
        return 2


_DRIFT_BLOCKED_HOSTS = frozenset(
    {
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "youtube.com",
        "youtu.be",
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "reddit.com",
        "linkedin.com",
    }
)


def _host_from_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").replace("www.", "").lower()
    except Exception:
        return ""


def _allowed_domains_from_seeds(seeds: list[str]) -> list[str]:
    hosts: list[str] = []
    for seed in seeds:
        host = _host_from_url(seed)
        if host:
            hosts.append(host)
    return list(dict.fromkeys(hosts))


def _is_trusted_crawl_url(url: str, allowed_domains: list[str] | None = None) -> bool:
    host = _host_from_url(url)
    if not host:
        return False
    if any(host == blocked or host.endswith(f".{blocked}") for blocked in _DRIFT_BLOCKED_HOSTS):
        return False
    if allowed_domains:
        return any(host == d or host.endswith(f".{d}") for d in allowed_domains)
    return True


def _filter_crawl_documents(
    docs: list[CrawledDocument],
    *,
    allowed_domains: list[str] | None = None,
) -> list[CrawledDocument]:
    return [d for d in docs if _is_trusted_crawl_url(d.url, allowed_domains)]


def _question_focus_terms(question: str) -> list[str]:
    stop = frozenset(
        {
            "what",
            "why",
            "how",
            "when",
            "where",
            "who",
            "the",
            "and",
            "for",
            "are",
            "was",
            "were",
            "about",
            "explain",
            "describe",
        }
    )
    terms = [w for w in re.split(r"\W+", question.lower()) if len(w) > 2 and w not in stop]
    return terms[:8]


def augment_seeds_for_question(seeds: list[str], question: str) -> list[str]:
    """Mirror OmniSpider retrieval-ranker — add site search URLs for the topic."""
    terms = _question_focus_terms(question)
    raw_focus = " ".join(terms) or question.strip()
    query = quote(raw_focus or question)
    out: set[str] = set(seeds)

    for seed in seeds:
        try:
            host = (urlparse(seed).hostname or "").replace("www.", "").lower()
            if host == "arxiv.org":
                out.add(f"https://arxiv.org/search/?query={query}&searchtype=all")
            if host == "paperswithcode.com":
                out.add(f"https://paperswithcode.com/search?q={query}")
            if "pubmed.ncbi.nlm.nih.gov" in host:
                out.add(f"https://pubmed.ncbi.nlm.nih.gov/?term={query}")
            if "britannica.com" in host:
                out.add(f"https://www.britannica.com/search?query={query}")
                for term in terms[:2]:
                    slug = term.rstrip("s")
                    out.add(f"https://www.britannica.com/science/{slug}")
                    out.add(f"https://www.britannica.com/topic/{slug}")
            if "worldhistory.org" in host:
                out.add(f"https://www.worldhistory.org/search/?q={query}")
            if "investopedia.com" in host:
                out.add(f"https://www.investopedia.com/search?q={query}")
            if "wikipedia.org" in host:
                lang = host.split(".")[0]
                out.add(f"https://{lang}.wikipedia.org/wiki/Special:Search?search={query}")
        except Exception:
            continue

    return list(out)


def resolve_seeds_for_domain(domain: str) -> list[str]:
    """Fetch whitelisted seed URLs from OmniSpider domain-seeds config."""
    if not domain.strip():
        return []
    url = f"{_api_base()}/v1/domain-seeds/{requests.utils.quote(domain.strip(), safe='')}"
    try:
        response = requests.get(url, headers=_headers(), timeout=15)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        seeds = payload.get("seeds") if isinstance(payload, dict) else None
        return [str(s) for s in seeds if s] if isinstance(seeds, list) else []
    except requests.RequestException:
        logger.debug("OmniSpider domain-seeds lookup failed for %s", domain, exc_info=True)
        return []


def crawl_for_question(question: str, domain: str) -> list[CrawledDocument]:
    """
    Crawl trusted whitelist sites for ``domain`` using ``question`` as the topic filter.
    Returns cleaned text documents with source URLs.
    """
    if not omnispider_enabled():
        return []
    question = (question or "").strip()
    domain = (domain or "").strip()
    if not question:
        return []

    payload: dict[str, Any] = {
        "topic": question,
        "domain": domain,
        "maxDepth": _max_depth(),
        "maxPages": _max_pages(),
        "timeoutMs": int(_timeout_sec() * 1000),
        "pollMs": int(_poll_interval_sec() * 1000),
        "pageLimit": _max_pages(),
    }

    try:
        response = requests.post(
            f"{_api_base()}/api/crawl",
            json=payload,
            headers=_headers(),
            timeout=_timeout_sec() + 15,
        )
        if response.status_code == 504:
            logger.warning("OmniSpider crawl timed out for domain=%s", domain)
            return []
        response.raise_for_status()
        body = response.json()
        docs_raw = body.get("documents") if isinstance(body, dict) else None
        if not isinstance(docs_raw, list):
            return []
        seeds = resolve_seeds_for_domain(domain)
        allowed = _allowed_domains_from_seeds(seeds)
        out: list[CrawledDocument] = []
        for item in docs_raw:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            url = str(item.get("url") or "").strip()
            if len(text) < 80 or not _is_trusted_crawl_url(url, allowed):
                continue
            out.append(
                CrawledDocument(
                    text=text,
                    url=url,
                    title=str(item.get("title") or url or "crawled page"),
                    source=str(item.get("source") or "omnispider"),
                )
            )
        return out
    except requests.RequestException:
        logger.warning("OmniSpider /api/crawl failed; trying job API", exc_info=True)
        return _crawl_via_jobs(question, domain)


def _crawl_via_jobs(question: str, domain: str) -> list[CrawledDocument]:
    """Fallback: POST /v1/jobs, poll status, GET pages with includeText."""
    seeds = augment_seeds_for_question(resolve_seeds_for_domain(domain), question)
    if not seeds:
        return []
    allowed = _allowed_domains_from_seeds(seeds)

    try:
        create = requests.post(
            f"{_api_base()}/v1/jobs",
            json={
                "seeds": seeds,
                "topic": question,
                "maxDepth": _max_depth(),
                "maxPages": _max_pages(),
                "includeArchive": False,
                "includeSitemaps": False,
                "topicFollowRelated": False,
                "allowedDomains": allowed,
            },
            headers=_headers(),
            timeout=30,
        )
        create.raise_for_status()
        job = create.json()
        job_id = str(job.get("id") or "")
        if not job_id:
            return []

        deadline = time.monotonic() + _timeout_sec()
        status = str(job.get("status") or "pending")
        while status in ("pending", "running") and time.monotonic() < deadline:
            time.sleep(_poll_interval_sec())
            poll = requests.get(
                f"{_api_base()}/v1/jobs/{job_id}",
                headers=_headers(),
                timeout=15,
            )
            poll.raise_for_status()
            status = str(poll.json().get("status") or "")
        if status != "completed":
            return []

        pages = requests.get(
            f"{_api_base()}/v1/jobs/{job_id}/pages",
            params={"limit": _max_pages(), "includeText": "true"},
            headers=_headers(),
            timeout=30,
        )
        pages.raise_for_status()
        rows = pages.json()
        if not isinstance(rows, list):
            return []

        out: list[CrawledDocument] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            url = str(row.get("finalUrl") or row.get("url") or "").strip()
            if len(text) < 80 or not _is_trusted_crawl_url(url, allowed):
                continue
            out.append(
                CrawledDocument(
                    text=text,
                    url=url,
                    title=str(row.get("title") or url or "crawled page"),
                )
            )
        return out
    except requests.RequestException:
        logger.warning("OmniSpider job crawl failed for domain=%s", domain, exc_info=True)
        return []


def persist_crawl_documents(docs: list[CrawledDocument], domain_slug: str) -> int:
    """Store crawled pages in PostgreSQL for future instant retrieval."""
    if not docs:
        return 0

    from sqlalchemy import select

    from db.models import Document, KnowledgeDomain
    from db.session import get_session
    from pipeline.step1_collection.filters import filter_document
    from pipeline.step1_collection.collectors import RawDocument

    parts = [p for p in domain_slug.split(".") if p]
    top_domain = parts[0] if parts else domain_slug

    saved = 0
    try:
        with get_session() as session:
            domain_row = session.scalar(
                select(KnowledgeDomain).where(KnowledgeDomain.slug == top_domain)
            )
            domain_id = domain_row.id if domain_row else None

            for doc in docs:
                if not _is_trusted_crawl_url(doc.url):
                    continue
                raw = RawDocument(
                    doc_id=f"omnispider_{hashlib.sha256(doc.url.encode()).hexdigest()[:16]}",
                    source="omnispider",
                    title=doc.title[:512],
                    text=doc.text,
                    url=doc.url[:1024] if doc.url else None,
                    metadata={
                        "domain": top_domain,
                        "domain_path": domain_slug,
                        "crawl_source": doc.source,
                    },
                )
                ok, quality, _reason = filter_document(raw)
                if not ok:
                    continue
                digest = raw.content_hash()
                if session.scalar(select(Document).where(Document.content_hash == digest)):
                    continue
                session.add(
                    Document(
                        domain_id=domain_id,
                        source=raw.source,
                        title=raw.title,
                        text=raw.text,
                        url=raw.url,
                        language=raw.language,
                        quality_score=quality,
                        verified=False,
                        content_hash=digest,
                        extra=raw.metadata,
                    )
                )
                try:
                    session.commit()
                    saved += 1
                except Exception:
                    session.rollback()
    except Exception:
        logger.exception("Failed to persist OmniSpider documents for %s", domain_slug)
        return 0

    if saved:
        try:
            from brain.vector_rag import invalidate_rag_index

            invalidate_rag_index()
        except Exception:
            logger.debug("RAG invalidate after crawl persist skipped", exc_info=True)
    return saved
