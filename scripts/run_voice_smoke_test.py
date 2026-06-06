#!/usr/bin/env python3
"""Smoke test — five questions, no source labels in prose."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chat_service import chat  # noqa: E402

QUESTIONS = [
    "What happened in the tech world today?",
    "If you could choose between Religion or Spiritually, what would you choose?",
    "Can you tell me about history about the CIA STARGATE PROJECT",
    "Why did the Roman Empire fall?",
    "What is photosynthesis?",
]

_BANNED = re.compile(
    r"wikipedia|according to|based on \d+ source|from what i['']ve collected|"
    r"\bsources:\s|google said|page said|\bcia:\s|\breuters\b",
    re.I,
)


def main() -> int:
    os.environ.setdefault("AUREON_WEB_SEARCH_ENABLED", "1")
    failed = 0
    for i, q in enumerate(QUESTIONS, start=1):
        r = chat(q, session_id=f"voice-smoke-{i}")
        reply = str(r.get("reply", ""))
        bad = _BANNED.search(reply)
        status = "PASS" if not bad and len(reply) > 30 else "FAIL"
        if status == "FAIL":
            failed += 1
        print(f"[{i}/5] {status}  kind={r.get('kind')}")
        print(f"  Q: {q}")
        print(f"  A: {reply[:220]}{'...' if len(reply) > 220 else ''}")
        if bad:
            print(f"  !! banned pattern: {bad.group(0)!r}")
        print()
    print(f"Done: {5 - failed}/5 passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
