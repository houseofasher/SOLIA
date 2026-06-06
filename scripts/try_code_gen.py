"""Quick script — run code generation and print evaluation."""

from __future__ import annotations

import json
import os
import warnings

# Fast local settings (same spirit as tests/conftest.py)
os.environ.setdefault("AUREON_PREDICT_EPOCHS", "40")
os.environ.setdefault("AUREON_PREDICT_TRAIN_CHUNK", "64")
os.environ.setdefault("AUREON_PREDICT_MAX_SEQ", "128")
os.environ.setdefault("AUREON_PREDICT_MAX_VOCAB", "2000")
os.environ.setdefault("AUREON_PREDICT_TRAIN_MAX_VOCAB", "2000")
os.environ.setdefault("AUREON_PREDICT_D_MODEL", "48")
os.environ.setdefault("AUREON_PREDICT_LAYERS", "4")
os.environ.setdefault("AUREON_PREDICT_D_FF", "128")
os.environ.setdefault("AUREON_ABSTAIN_THRESHOLD", "0.05")
os.environ.setdefault("AUREON_PREDICT_ABSTAIN_MIN_RAG", "0.0")
os.environ.setdefault("AUREON_PREDICT_ABSTAIN_MIN_PROB", "0.0")

warnings.filterwarnings("ignore")

from brain.code_evaluator import evaluate_code_response, extract_python_code
from brain.predict_engine import _bootstrap_answer, predict_with_steps

PROMPTS = [
    "write a python function to add two numbers",
    "write a python function to reverse a string",
    "write a python function to check if a number is even",
    "write a python function to find all prime numbers up to n",
    "implement a python function to sort a list",
]


def main() -> None:
    print("=== BOOTSTRAP FALLBACKS (seed lines) ===\n")
    for q in PROMPTS:
        bootstrap = _bootstrap_answer(q)
        ev = evaluate_code_response(bootstrap or "", None)
        print(f"Q: {q}")
        print(f"  bootstrap: {bootstrap!r}")
        print(f"  syntax_valid={ev.get('syntax_valid')} score={ev.get('score')}\n")

    print("=== FULL PREDICT PIPELINE ===\n")
    for q in PROMPTS:
        print("=" * 60)
        print("Q:", q)
        result = predict_with_steps(q, force=True)
        if not result:
            print("  -> None (abstained)\n")
            continue
        raw = result.get("answer", "")
        code = extract_python_code(raw)
        ev = evaluate_code_response(code)
        print("  raw:", repr(raw[:350]))
        print("  code:", code or "(empty)")
        print("  confidence:", result.get("confidence"), "abstained:", result.get("abstained"))
        print("  eval:", json.dumps({k: v for k, v in ev.items() if k != "stderr"}))
        cites = result.get("citations") or []
        if cites:
            top = cites[0]
            print("  top cite:", top.get("title"), "|", top.get("source"), "| score", top.get("score"))
        print()


if __name__ == "__main__":
    main()
