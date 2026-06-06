#!/usr/bin/env python3
"""Run verified multi-language coding prompts through Aureon and judge each response."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chat_service import chat
from brain.code_catalog import CODE_TASKS, SUPPORTED_LANGUAGES
from brain.code_languages import (
    build_multilang_prompt,
    check_code_security,
    detect_code_language,
    detect_code_task,
    evaluate_multilang,
    extract_code,
    runtime_available,
)

_LANG_LABELS = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "go": "Go",
    "rust": "Rust",
    "cpp": "C++",
}


def run_case(language: str, task: str) -> dict:
    prompt = build_multilang_prompt(_LANG_LABELS[language], task)
    result = chat(prompt, session_id=f"ml-{language}-{task}")
    code = extract_code(result.get("reply", ""), language)
    from brain.code_catalog import get_catalog_entry

    entry = get_catalog_entry(language, task)
    tests = entry["tests"] if entry else ""
    security = check_code_security(code, language)
    evaluation = evaluate_multilang(code, language, tests, task=task) if tests else {}
    passed = (
        result.get("kind") == "code"
        and security.get("safe") is True
        and evaluation.get("passed_tests") is True
        and len(code.strip()) > 10
    )
    return {
        "language": language,
        "task": task,
        "prompt": prompt,
        "kind": result.get("kind"),
        "method": (result.get("code_master") or {}).get("method"),
        "security_ok": security.get("safe"),
        "passed_tests": evaluation.get("passed_tests"),
        "validated": evaluation.get("validated"),
        "runtime": runtime_available(language),
        "passed": passed,
        "code": code,
        "stderr": evaluation.get("stderr", security.get("error", "")),
    }


def main() -> int:
    results = []
    passed = 0
    total = len(SUPPORTED_LANGUAGES) * len(CODE_TASKS)

    print(f"Runtimes: {', '.join(f'{lang}={runtime_available(lang)}' for lang in SUPPORTED_LANGUAGES)}")
    print(f"Testing {total} language/task pairs...\n")

    for language in SUPPORTED_LANGUAGES:
        for task in CODE_TASKS:
            row = run_case(language, task)
            results.append(row)
            if row["passed"]:
                passed += 1
            status = "PASS" if row["passed"] else "FAIL"
            print(f"[{status}] {language}/{task} ({row['method'] or row['kind']})")
            if not row["passed"]:
                print(f"  security={row['security_ok']} tests={row['passed_tests']} runtime={row['runtime']}")
                if row["stderr"]:
                    print(f"  err: {str(row['stderr'])[:120]}")
                print(f"  code: {row['code'][:120]}...")

    print(f"\n{'=' * 60}")
    print(f"Summary: {passed}/{total} passed")
    out = ROOT / "data" / "audit" / "multilang-code-test.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
