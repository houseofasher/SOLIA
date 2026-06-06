#!/usr/bin/env python3
"""Run 100 human-domain questions and audit whether Aureon actually answers them."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chat_service import chat  # noqa: E402
from brain.response_quality import audit_response  # noqa: E402
from scripts.human_domain_questions import all_questions  # noqa: E402


def main() -> int:
    os.environ.setdefault("AUREON_WEB_SEARCH_ENABLED", "1")
    os.environ.setdefault("AUREON_PREDICT_TIMEOUT_SEC", "6")

    results: list[dict] = []
    passed = 0
    failed = 0
    recovered = 0

    for idx, (domain, question) in enumerate(all_questions(), start=1):
        sid = f"audit-{domain}-{idx}"
        started = time.time()
        try:
            payload = chat(question, session_id=sid)
        except Exception as exc:
            payload = {"reply": str(exc), "kind": "error"}
        elapsed = round(time.time() - started, 2)
        reply = str(payload.get("reply", ""))
        audit = audit_response(question, reply, payload)
        if payload.get("quality_recovered"):
            recovered += 1
        row = {
            "domain": domain,
            "question": question,
            "adequate": audit.adequate,
            "reasons": audit.reasons,
            "intent": audit.intent.value,
            "kind": payload.get("kind"),
            "recovered": bool(payload.get("quality_recovered")),
            "reply_preview": reply[:180],
            "elapsed_sec": elapsed,
        }
        results.append(row)
        if audit.adequate:
            passed += 1
        else:
            failed += 1
        status = "PASS" if audit.adequate else "FAIL"
        print(f"[{idx:3d}/100] {status} {domain}: {question[:60]}... ({elapsed}s)", flush=True)

    report = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "recovered": recovered,
        "pass_rate": round(passed / max(len(results), 1), 3),
        "results": results,
    }

    out_path = ROOT / "data" / "audit" / "human-domain-audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    print(f"Passed: {passed}/100  Failed: {failed}/100  Recovered: {recovered}")
    print(f"Report: {out_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
