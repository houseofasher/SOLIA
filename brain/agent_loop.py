"""Agent tool loop — multi-step plans with search, calculate, verify gates."""

from __future__ import annotations

import re
from typing import Any, Callable

from brain.brain_classifiers import classify_moe
from brain.deterministic_qa import try_arithmetic_answer
from brain.predict_engine import predict_with_steps
from brain.vector_rag import retrieve_with_citations

ToolFn = Callable[..., dict[str, Any]]


def _tool_rag_search(query: str) -> dict[str, Any]:
    context, hits, citations = retrieve_with_citations(query, top_k=6)
    return {
        "tool": "rag_search",
        "ok": bool(hits),
        "hits": len(hits),
        "context_words": len(context.split()) if context else 0,
        "citations": citations[:5],
        "preview": hits[0].snippet(200) if hits else "",
    }


def _tool_calculate(expression: str) -> dict[str, Any]:
    result = try_arithmetic_answer(f"what is {expression.strip()}")
    if not result:
        result = try_arithmetic_answer(expression.strip())
    return {
        "tool": "calculate",
        "ok": result is not None,
        "expression": expression,
        "answer": result["answer"] if result else None,
    }


def _tool_classify(text: str) -> dict[str, Any]:
    result = classify_moe(text)
    return {"tool": "classify", "ok": result is not None, "classification": result}


def _tool_verify(citations: list[dict[str, Any]], answer: str) -> dict[str, Any]:
    grounded = bool(citations) and len(answer.strip()) >= 3
    has_hash = all(c.get("content_hash") for c in citations) if citations else False
    return {
        "tool": "verify",
        "ok": grounded and has_hash,
        "grounded": grounded,
        "citation_count": len(citations),
        "verified_hashes": has_hash,
    }


def _extract_math_expression(text: str) -> str | None:
    match = re.search(r"([\d\s+\-*/().%]+)", text)
    if not match:
        return None
    expr = match.group(1).strip()
    return expr if re.search(r"[+\-*/%]", expr) else None


def is_agent_task(text: str) -> bool:
    """True for multi-step or explicit agent requests."""
    lower = text.strip().lower()
    if lower.startswith("/agent"):
        return True
    triggers = (
        "first search",
        "then calculate",
        "step by step",
        "multi-step",
        "use tools",
        "search and",
        "find and explain",
    )
    return any(t in lower for t in triggers)


def run_agent_loop(question: str, *, max_steps: int = 5) -> dict[str, Any]:
    """
    Plan → execute tools → verify → synthesize answer.
    Tools: rag_search, calculate, classify, predict, verify.
    """
    q = question.strip()
    if q.lower().startswith("/agent"):
        q = q[6:].strip(" :")

    steps: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    answer: str | None = None
    confidence = 0.0
    expr = _extract_math_expression(q)

    # Step 1 — corpus search
    rag = _tool_rag_search(q)
    steps.append(rag)
    citations = list(rag.get("citations") or [])

    # Step 2 — arithmetic (exact evaluators first)
    arith = try_arithmetic_answer(q)
    if arith:
        steps.append(
            {
                "tool": "calculate",
                "ok": True,
                "expression": q,
                "answer": arith["answer"],
            }
        )
        answer = str(arith["answer"])
    elif expr and len(steps) < max_steps:
        calc = _tool_calculate(expr)
        steps.append(calc)
        if calc.get("ok"):
            answer = str(calc["answer"])

    # Step 3 — domain classification
    if len(steps) < max_steps:
        clf = _tool_classify(q)
        steps.append(clf)

    # Step 4 — predict brain if no arithmetic answer
    if not answer and len(steps) < max_steps:
        pred = predict_with_steps(q)
        if pred:
            steps.append(
                {
                    "tool": "predict",
                    "ok": not pred.get("abstained", False),
                    "confidence": pred.get("confidence"),
                    "abstained": pred.get("abstained", False),
                }
            )
            answer = pred.get("answer")
            confidence = float(pred.get("confidence") or 0.0)
            citations = list(pred.get("citations") or citations)

    if not answer:
        answer = "I couldn't complete the agent plan with grounded tools."

    # Step 5 — verification gate
    if len(steps) < max_steps:
        verify = _tool_verify(citations, answer)
        steps.append(verify)
        if (
            not verify.get("ok")
            and not try_arithmetic_answer(q)
            and not answer.replace(".", "", 1).isdigit()
        ):
            answer = "I don't know — agent verification failed (no auditable citations)."

    return {
        "answer": answer,
        "plan": [s["tool"] for s in steps],
        "steps": steps,
        "citations": citations,
        "confidence": confidence,
        "agent": True,
        "max_steps": max_steps,
    }
