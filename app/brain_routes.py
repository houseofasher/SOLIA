"""Brain API helpers."""

from __future__ import annotations

from typing import Any

from brain.domains.taxonomy import (
    KNOWLEDGE_TAXONOMY,
    total_micro_subdomains,
    total_subdomains,
)


def get_taxonomy() -> dict[str, Any]:
    return {
        "hierarchy": "domain → subdomain → micro_subdomain",
        "domains": KNOWLEDGE_TAXONOMY,
        "domain_count": len(KNOWLEDGE_TAXONOMY),
        "subdomain_count": total_subdomains(),
        "micro_subdomain_count": total_micro_subdomains(),
    }
