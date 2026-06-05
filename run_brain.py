#!/usr/bin/env python3
"""CLI for the brain micro-algorithm architecture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from brain.cortex import (
    bootstrap_brain,
    brain_status,
    run_domain_cycle,
    run_full_brain,
    run_micro_subdomain_cycle,
    run_subdomain_cycle,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aureon brain — domain → subdomain → micro-subdomain micro-agents"
    )
    parser.add_argument("--bootstrap", action="store_true", help="Seed DB with full taxonomy")
    parser.add_argument("--status", action="store_true", help="Show brain status")
    parser.add_argument("--domain", type=str, help="Run one domain")
    parser.add_argument("--subdomain", type=str, help="Run one subdomain (requires --domain)")
    parser.add_argument("--micro-subdomain", type=str, help="Run one micro-subdomain (requires --domain and --subdomain)")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--domain-limit", type=int, default=3)
    parser.add_argument("--subdomain-limit", type=int, default=1)
    parser.add_argument("--micro-subdomain-limit", type=int, default=1)
    args = parser.parse_args()

    if args.bootstrap:
        print(json.dumps(bootstrap_brain(), indent=2))
        return
    if args.status:
        print(json.dumps(brain_status(), indent=2))
        return
    if args.domain and args.subdomain and args.micro_subdomain:
        print(
            json.dumps(
                run_micro_subdomain_cycle(
                    args.domain,
                    args.subdomain,
                    args.micro_subdomain,
                    epochs=args.epochs,
                ),
                indent=2,
            )
        )
        return
    if args.domain and args.subdomain:
        print(
            json.dumps(
                run_subdomain_cycle(
                    args.domain,
                    args.subdomain,
                    epochs=args.epochs,
                    micro_subdomain_limit=args.micro_subdomain_limit,
                ),
                indent=2,
            )
        )
        return
    if args.domain:
        print(
            json.dumps(
                run_domain_cycle(
                    args.domain,
                    epochs=args.epochs,
                    subdomain_limit=args.subdomain_limit,
                    micro_subdomain_limit=args.micro_subdomain_limit,
                ),
                indent=2,
            )
        )
        return

    print(
        json.dumps(
            run_full_brain(
                epochs=args.epochs,
                domain_limit=args.domain_limit,
                subdomain_limit=args.subdomain_limit,
                micro_subdomain_limit=args.micro_subdomain_limit,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
