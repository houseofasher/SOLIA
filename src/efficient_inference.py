"""Efficient inference helpers — sliding-window attention and speculative decode."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from src.neural_network import softmax


def attention_window() -> int:
    raw = os.environ.get("AUREON_ATTENTION_WINDOW", "512")
    try:
        return max(32, min(int(raw), 8192))
    except ValueError:
        return 512


def speculative_draft_tokens() -> int:
    raw = os.environ.get("AUREON_SPECULATIVE_DRAFT", "2")
    try:
        return max(1, min(int(raw), 8))
    except ValueError:
        return 2


def sliding_window_attention(
    x: np.ndarray,
    *,
    window: int,
    softmax_3d,
) -> tuple[np.ndarray, np.ndarray]:
    """
    O(seq × window) causal self-attention — enables 1M context config
    without materializing full seq×seq matrices.
    Expects layer-normalized x.
    """
    batch, seq, d_model = x.shape
    out = np.zeros_like(x)
    weights_out = np.zeros((batch, seq, seq), dtype=float)

    for q in range(seq):
        start = max(0, q - window + 1)
        keys = x[:, start : q + 1, :]
        query = x[:, q : q + 1, :]
        scores = (query @ np.swapaxes(keys, -1, -2)) / np.sqrt(d_model)
        scores = np.clip(scores, -40.0, 40.0)
        w = softmax_3d(scores)
        out[:, q : q + 1, :] = w @ keys
        weights_out[:, q, start : q + 1] = w[0, 0]

    return out, weights_out


def truncate_tokens_for_inference(token_ids: list[int], *, max_window: int) -> list[int]:
    """Keep BOS + tail within attention window."""
    if len(token_ids) <= max_window:
        return token_ids
    bos = token_ids[0]
    tail = token_ids[-(max_window - 1) :]
    if tail and tail[0] == bos:
        return tail
    return [bos, *tail]


def inference_profile(seq_len: int, *, window: int | None = None) -> dict[str, Any]:
    window = window or attention_window()
    dense_cost = seq_len * seq_len
    sparse_cost = seq_len * min(seq_len, window)
    return {
        "seq_len": seq_len,
        "attention_window": window,
        "dense_attention_cost": dense_cost,
        "sparse_attention_cost": sparse_cost,
        "speedup_vs_dense": round(dense_cost / max(sparse_cost, 1), 2),
        "mode": "sliding_window" if seq_len > window else "dense",
    }
