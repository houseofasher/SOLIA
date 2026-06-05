"""Generate micro-subdomain slugs for every domain/subdomain pair."""

from __future__ import annotations

from brain.domains.subdomains import SUBDOMAIN_TAXONOMY

# Hand-crafted micro-subdomains for high-signal topics.
MICRO_OVERRIDES: dict[tuple[str, str], list[str]] = {
    ("mathematics", "algebra"): ["linear_algebra", "abstract_algebra", "group_theory"],
    ("mathematics", "calculus"): ["differential_calculus", "integral_calculus", "multivariable_calculus"],
    ("mathematics", "geometry"): ["euclidean_geometry", "differential_geometry", "algebraic_geometry"],
    ("mathematics", "statistics"): ["descriptive_statistics", "inferential_statistics", "bayesian_statistics"],
    ("computer_science", "algorithms"): ["sorting_search", "graph_algorithms", "complexity_theory"],
    ("computer_science", "machine_learning"): ["supervised_learning", "unsupervised_learning", "reinforcement_learning"],
    ("computer_science", "security"): ["cryptography", "network_security", "application_security"],
    ("computer_science", "databases"): ["relational_databases", "query_optimization", "distributed_databases"],
    ("biology", "genetics"): ["mendelian_genetics", "molecular_genetics", "population_genetics"],
    ("biology", "neuroscience"): ["cellular_neuroscience", "cognitive_neuroscience", "computational_neuroscience"],
    ("physics", "quantum_mechanics"): ["wave_mechanics", "quantum_field_theory", "quantum_information"],
    ("physics", "classical_mechanics"): ["newtonian_mechanics", "lagrangian_mechanics", "hamiltonian_mechanics"],
    ("linguistics", "syntax"): ["generative_syntax", "dependency_syntax", "morphosyntax"],
    ("linguistics", "sanskrit_studies"): ["panini_grammar", "sanskrit_phonology", "sanskrit_semantics"],
    ("vedic_sciences", "astronomy_jyotisha"): ["natal_chart", "dashas_transits", "muhurta_electional"],
    ("vedic_sciences", "grammar_vyakarana"): ["sandhi_rules", "karaka_analysis", "sutra_commentary"],
    ("vedic_sciences", "philosophy_darshana"): ["nyaya_logic", "vedanta_metaphysics", "samkhya_cosmology"],
    ("psychology", "cognitive"): ["memory", "attention", "decision_making"],
    ("economics", "microeconomics"): ["consumer_theory", "producer_theory", "market_equilibrium"],
    ("economics", "macroeconomics"): ["monetary_policy", "fiscal_policy", "growth_models"],
    ("medicine", "pharmacology"): ["pharmacokinetics", "pharmacodynamics", "clinical_pharmacology"],
    ("law", "constitutional"): ["rights_jurisprudence", "separation_powers", "judicial_review"],
    ("philosophy", "ethics"): ["normative_ethics", "metaethics", "applied_ethics"],
    ("engineering", "control_systems"): ["feedback_control", "state_space", "optimal_control"],
    ("business", "marketing"): ["consumer_behavior", "brand_strategy", "digital_marketing"],
}


def micro_subdomains_for(domain: str, subdomain: str) -> list[str]:
    key = (domain, subdomain)
    if key in MICRO_OVERRIDES:
        return MICRO_OVERRIDES[key]
    return [
        f"{subdomain}_fundamentals",
        f"{subdomain}_methods",
        f"{subdomain}_applications",
    ]


def build_full_taxonomy() -> dict[str, dict[str, list[str]]]:
    return {
        domain: {sub: micro_subdomains_for(domain, sub) for sub in subs}
        for domain, subs in SUBDOMAIN_TAXONOMY.items()
    }
