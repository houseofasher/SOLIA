"""Sovereign organism organ registry — nomad_cyber_algorithm dependency graph (Aureon-adapted)."""

from __future__ import annotations

from typing import Literal

OrganId = Literal[
    "supply_spleen",
    "audit_immune",
    "bootstrap_heart",
    "auth_gateway",
    "replay_guard",
    "rate_limit_nerves",
    "database_marrow",
    "training_lock",
    "gateway_skin",
    "vault_marrow",
    "activity_lungs",
]

OrganState = Literal["vital", "dormant", "critical", "pending"]

ORGAN_META: dict[OrganId, dict[str, str]] = {
    "supply_spleen": {
        "name": "Supply Spleen",
        "role": "Dependency integrity (requirements.txt hash)",
    },
    "audit_immune": {
        "name": "Audit Immune System",
        "role": "Tamper-evident HMAC-chained audit log",
    },
    "bootstrap_heart": {
        "name": "Bootstrap Heart",
        "role": "Railway/runtime secret and database bootstrap",
    },
    "auth_gateway": {
        "name": "Auth Gateway",
        "role": "API key perimeter for mutating routes",
    },
    "replay_guard": {
        "name": "Replay Cortex",
        "role": "Timestamp + nonce anti-replay on signed requests",
    },
    "rate_limit_nerves": {
        "name": "Rate Limit Nerves",
        "role": "Per-IP sliding window on mutating routes",
    },
    "database_marrow": {
        "name": "Database Marrow",
        "role": "Persistent brain storage connectivity",
    },
    "training_lock": {
        "name": "Training Spleen",
        "role": "Exclusive training lock — one job at a time",
    },
    "gateway_skin": {
        "name": "Gateway Skin",
        "role": "HTTP security middleware perimeter",
    },
    "vault_marrow": {
        "name": "Vault Marrow",
        "role": "Secrets vault bound to organism fingerprint",
    },
    "activity_lungs": {
        "name": "Activity Lungs",
        "role": "Structured AI activity logging (Railway observability)",
    },
}

ORGAN_DEPENDENCIES: dict[OrganId, list[OrganId]] = {
    "supply_spleen": [],
    "audit_immune": ["supply_spleen"],
    "bootstrap_heart": ["audit_immune"],
    "auth_gateway": ["bootstrap_heart"],
    "replay_guard": ["audit_immune", "auth_gateway"],
    "rate_limit_nerves": ["audit_immune"],
    "database_marrow": ["audit_immune"],
    "training_lock": ["database_marrow"],
    "gateway_skin": ["auth_gateway", "rate_limit_nerves", "replay_guard"],
    "vault_marrow": ["audit_immune", "bootstrap_heart"],
    "activity_lungs": ["audit_immune"],
}

NOMAD_DOCTRINE = (
    "Partial compromise = total shutdown for mutating operations. "
    "Breach the audit chain → lockdown. Lose database marrow → lockdown. "
    "An attacker must defeat all interlocking organs simultaneously — "
    "auth gateway, replay guard, rate nerves, audit immune, vault marrow, and gateway skin."
)


def organ_activation_order() -> list[OrganId]:
    visited: set[OrganId] = set()
    order: list[OrganId] = []

    def visit(organ_id: OrganId) -> None:
        if organ_id in visited:
            return
        for dep in ORGAN_DEPENDENCIES[organ_id]:
            visit(dep)
        visited.add(organ_id)
        order.append(organ_id)

    for organ_id in ORGAN_DEPENDENCIES:
        visit(organ_id)
    return order


def dependencies_satisfied(organ_id: OrganId, statuses: dict[OrganId, OrganState]) -> bool:
    return all(statuses.get(dep) in ("vital", "dormant") for dep in ORGAN_DEPENDENCIES[organ_id])
