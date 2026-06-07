"""Prioritize auto-learn targets that lack OmniSpider corpus coverage."""

from __future__ import annotations

from sqlalchemy import func, select

from db.models import Document, KnowledgeDomain, KnowledgeMicroSubdomain, KnowledgeSubdomain
from db.session import get_session


def _path_key(domain: str, subdomain: str, micro: str) -> tuple[str, str, str]:
    return (domain, subdomain, micro)


def document_counts_for_targets(
    targets: list[tuple[str, str, str]],
) -> dict[tuple[str, str, str], int]:
    """Return document counts for each (domain, subdomain, micro) triple."""
    if not targets:
        return {}

    counts = {t: 0 for t in targets}
    try:
        with get_session() as session:
            rows = session.execute(
                select(
                    KnowledgeDomain.slug,
                    KnowledgeSubdomain.slug,
                    KnowledgeMicroSubdomain.slug,
                    func.count(Document.id),
                )
                .select_from(Document)
                .join(KnowledgeDomain, Document.domain_id == KnowledgeDomain.id)
                .join(KnowledgeSubdomain, Document.subdomain_id == KnowledgeSubdomain.id, isouter=True)
                .join(
                    KnowledgeMicroSubdomain,
                    Document.micro_subdomain_id == KnowledgeMicroSubdomain.id,
                    isouter=True,
                )
                .group_by(
                    KnowledgeDomain.slug,
                    KnowledgeSubdomain.slug,
                    KnowledgeMicroSubdomain.slug,
                )
            ).all()
            for domain_slug, sub_slug, micro_slug, count in rows:
                key = (
                    str(domain_slug or ""),
                    str(sub_slug or ""),
                    str(micro_slug or ""),
                )
                if key in counts:
                    counts[key] = int(count or 0)
    except Exception:
        return counts
    return counts


def sort_targets_by_corpus_gap(
    targets: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Micro-topics with zero or thin corpus are crawled/trained first."""
    counts = document_counts_for_targets(targets)
    return sorted(targets, key=lambda t: (counts.get(t, 0), t[0], t[1], t[2]))
