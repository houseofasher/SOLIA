#!/usr/bin/env python3
"""Run 5 coding prompts through Aureon, judge with code_evaluator, report/fix gaps."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chat_service import chat
from brain.code_evaluator import evaluate_code_response, extract_python_code

PROMPTS: list[dict[str, str]] = [
    {
        "name": "add_two_numbers",
        "prompt": "Write a Python function to add two numbers.",
        "test": "assert add(2, 3) == 5\nassert add(-1, 1) == 0",
    },
    {
        "name": "is_palindrome",
        "prompt": "Write a Python function is_palindrome(s) that returns True if a string is a palindrome.",
        "test": (
            "assert is_palindrome('racecar') is True\n"
            "assert is_palindrome('hello') is False\n"
            "assert is_palindrome('') is True"
        ),
    },
    {
        "name": "fibonacci",
        "prompt": "Write a Python function fib(n) that returns the nth Fibonacci number (0-indexed: fib(0)=0, fib(1)=1).",
        "test": "assert fib(0) == 0\nassert fib(1) == 1\nassert fib(10) == 55",
    },
    {
        "name": "count_vowels",
        "prompt": "Write a Python function count_vowels(s) that counts vowels in a string (a,e,i,o,u case-insensitive).",
        "test": "assert count_vowels('hello') == 2\nassert count_vowels('AEIOU') == 5\nassert count_vowels('xyz') == 0",
    },
    {
        "name": "merge_sorted",
        "prompt": "Write a Python function merge_sorted(a, b) that merges two sorted lists into one sorted list.",
        "test": (
            "assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]\n"
            "assert merge_sorted([], [1]) == [1]\n"
            "assert merge_sorted([], []) == []"
        ),
    },
]


def run_case(case: dict[str, str], *, session_id: str) -> dict:
    result = chat(case["prompt"], session_id=session_id)
    code = extract_python_code(result.get("reply", ""))
    eval_with_test = evaluate_code_response(code, case["test"])
    return {
        "name": case["name"],
        "prompt": case["prompt"],
        "kind": result.get("kind"),
        "method": (result.get("code_master") or {}).get("method"),
        "syntax_valid": eval_with_test.get("syntax_valid"),
        "passed_tests": eval_with_test.get("passed_tests"),
        "score": eval_with_test.get("score"),
        "stderr": eval_with_test.get("stderr", ""),
        "code": code,
        "reply": result.get("reply", ""),
    }


def main() -> int:
    results = []
    passed = 0
    for i, case in enumerate(PROMPTS):
        row = run_case(case, session_id=f"code-test-{case['name']}")
        results.append(row)
        ok = row["passed_tests"] is True
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"\n[{status}] {row['name']} ({row['method'] or row['kind']})")
        print(f"  prompt: {row['prompt']}")
        if not ok:
            print(f"  syntax: {row['syntax_valid']}  stderr: {row['stderr'][:200]}")
        print(f"  code:\n{row['code'][:400]}")

    print(f"\n{'=' * 60}")
    print(f"Summary: {passed}/{len(PROMPTS)} passed")
    out = ROOT / "data" / "audit" / "code-coding-test.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0 if passed == len(PROMPTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
