"""Brain API helpers."""

from __future__ import annotations

from typing import Any

from brain.domains.taxonomy import (
    KNOWLEDGE_TAXONOMY,
    total_micro_subdomains,
    total_subdomains,
)
from brain.grades import curriculum_public
from brain.graduation import progress_report
from db.models import KnowledgeDomain, KnowledgeMicroSubdomain, KnowledgeSubdomain
from db.session import get_session
from sqlalchemy import select


def get_taxonomy() -> dict[str, Any]:
    return {
        "hierarchy": "domain → subdomain → micro_subdomain → grade",
        "domains": KNOWLEDGE_TAXONOMY,
        "domain_count": len(KNOWLEDGE_TAXONOMY),
        "subdomain_count": total_subdomains(),
        "micro_subdomain_count": total_micro_subdomains(),
        "grade_curriculum": curriculum_public(),
    }


def get_grade_progress(
    domain_slug: str,
    subdomain_slug: str,
    micro_subdomain_slug: str,
) -> dict[str, Any]:
    with get_session() as session:
        domain = session.scalar(
            select(KnowledgeDomain).where(KnowledgeDomain.slug == domain_slug)
        )
        if not domain:
            return {"error": f"unknown domain: {domain_slug}"}
        subdomain = session.scalar(
            select(KnowledgeSubdomain).where(
                KnowledgeSubdomain.domain_id == domain.id,
                KnowledgeSubdomain.slug == subdomain_slug,
            )
        )
        if not subdomain:
            return {"error": f"unknown subdomain: {subdomain_slug}"}
        micro = session.scalar(
            select(KnowledgeMicroSubdomain).where(
                KnowledgeMicroSubdomain.subdomain_id == subdomain.id,
                KnowledgeMicroSubdomain.slug == micro_subdomain_slug,
            )
        )
        if not micro:
            return {"error": f"unknown micro_subdomain: {micro_subdomain_slug}"}
        return progress_report(session, micro.id)
