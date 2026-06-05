"""Human knowledge taxonomy — domain → subdomain → micro-subdomain."""

from __future__ import annotations

from brain.domains.generate_micros import build_full_taxonomy
from brain.domains.subdomains import SUBDOMAIN_TAXONOMY

# domain → subdomain → [micro_subdomain, ...]
KNOWLEDGE_TAXONOMY: dict[str, dict[str, list[str]]] = build_full_taxonomy()


def all_domain_slugs() -> list[str]:
    return list(KNOWLEDGE_TAXONOMY.keys())


def subdomains_for(domain: str) -> list[str]:
    return list(KNOWLEDGE_TAXONOMY.get(domain, {}).keys())


def micro_subdomains_for(domain: str, subdomain: str) -> list[str]:
    return list(KNOWLEDGE_TAXONOMY.get(domain, {}).get(subdomain, []))


def all_subdomain_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for domain, subs in KNOWLEDGE_TAXONOMY.items():
        for sub in subs:
            pairs.append((domain, sub))
    return pairs


def all_micro_triples() -> list[tuple[str, str, str]]:
    triples: list[tuple[str, str, str]] = []
    for domain, subs in KNOWLEDGE_TAXONOMY.items():
        for sub, micros in subs.items():
            for micro in micros:
                triples.append((domain, sub, micro))
    return triples


def total_subdomains() -> int:
    return sum(len(subs) for subs in KNOWLEDGE_TAXONOMY.values())


def total_micro_subdomains() -> int:
    return sum(len(micros) for subs in KNOWLEDGE_TAXONOMY.values() for micros in subs.values())
