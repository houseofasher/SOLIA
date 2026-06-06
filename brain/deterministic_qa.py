"""Deterministic evaluators — exact answers before neural prediction."""

from __future__ import annotations

import ast
import operator
import re
from typing import Any

# Safe integer/float arithmetic only (+ - * / // % ** parentheses).
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_MATH_PREFIX = re.compile(
    r"^(?:what is|what's|whats|calculate|compute|evaluate|solve)\s+",
    re.IGNORECASE,
)
_EXPR_CHARS = re.compile(r"^[\d\s+\-*/().%]+$")
_HAS_OPERATOR = re.compile(r"[+\-*/%]")


def _normalize_expr(raw: str) -> str:
    text = raw.strip().lower().rstrip("?").strip()
    text = text.replace("×", "*").replace("÷", "/").replace("x", "*")
    text = _MATH_PREFIX.sub("", text).strip()
    return text


def _format_number(value: float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    rounded = round(value, 10)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded).rstrip("0").rstrip(".")


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("non-numeric constant")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return float(_UNARYOPS[type(node.op)](_safe_eval(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 20:
            raise ValueError("exponent too large")
        return float(_BINOPS[type(node.op)](left, right))
    raise ValueError("unsupported expression")


def try_arithmetic_answer(text: str) -> dict[str, Any] | None:
    """Return exact arithmetic result when the question is a math expression."""
    expr = _normalize_expr(text)
    if not expr or not _HAS_OPERATOR.search(expr):
        return None
    if not _EXPR_CHARS.match(expr):
        return None
    if len(expr) > 80:
        return None

    try:
        tree = ast.parse(expr, mode="eval")
        value = _safe_eval(tree.body)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None

    if not (-1e15 < value < 1e15):
        return None

    return {
        "answer": _format_number(value),
        "expression": expr,
        "evaluator": "deterministic_arithmetic",
    }


def is_arithmetic_question(text: str) -> bool:
    return try_arithmetic_answer(text) is not None
