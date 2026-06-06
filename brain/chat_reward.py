"""Chat RLHF — score replies and persist preference pairs for retraining."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from pipeline.config import MODELS_DIR, ensure_dirs
from pipeline.step5_rlhf.runner import DEFAULT_PREFERENCES, score_response, train_reward_model
from src.neural_network import NeuralNetwork
from src.text_features import TextFeatureExtractor

logger = logging.getLogger(__name__)

_reward_model: NeuralNetwork | None = None
_reward_extractor: TextFeatureExtractor | None = None


def _latest_reward_artifact() -> Path | None:
    ensure_dirs()
    dirs = sorted(MODELS_DIR.glob("reward_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for d in dirs:
        model = d / "reward_model.json"
        if model.is_file():
            return d
    return None


def get_chat_reward_model() -> tuple[NeuralNetwork, TextFeatureExtractor]:
    global _reward_model, _reward_extractor
    if _reward_model is not None and _reward_extractor is not None:
        return _reward_model, _reward_extractor

    artifact = _latest_reward_artifact()
    if artifact:
        _reward_model = NeuralNetwork.load(artifact / "reward_model.json")
        _reward_extractor = TextFeatureExtractor.from_dict(
            json.loads((artifact / "extractor.json").read_text(encoding="utf-8"))
        )
        return _reward_model, _reward_extractor

    _reward_model, _reward_extractor, _ = train_reward_model(
        DEFAULT_PREFERENCES, epochs=int(os.environ.get("AUREON_REWARD_EPOCHS", "120"))
    )
    run_dir = MODELS_DIR / "reward_chat"
    run_dir.mkdir(parents=True, exist_ok=True)
    _reward_model.save(run_dir / "reward_model.json")
    (run_dir / "extractor.json").write_text(
        json.dumps(_reward_extractor.to_dict(), indent=2), encoding="utf-8"
    )
    return _reward_model, _reward_extractor


def score_chat_reply(context: str, reply: str) -> dict[str, Any]:
    """Score a chat reply — higher is better."""
    model, extractor = get_chat_reward_model()
    score = score_response(model, extractor, context, reply)
    threshold = float(os.environ.get("AUREON_REWARD_GOOD_THRESHOLD", "0.55"))
    return {
        "score": round(score, 4),
        "good": score >= threshold,
        "threshold": threshold,
    }


def record_preference(
    *,
    context: str,
    preferred: str,
    rejected: str,
    domain_id: int | None = None,
) -> dict[str, Any]:
    """Store human or automated preference pair for RLHF retraining."""
    from db.session import get_session
    from db.models import PreferencePair

    with get_session() as session:
        session.add(
            PreferencePair(
                domain_id=domain_id,
                context=context[:4000],
                preferred=preferred[:4000],
                rejected=rejected[:4000],
            )
        )
        session.commit()
    return {"ok": True, "stored": True}


def apply_chat_reward(payload: dict[str, Any], user_message: str) -> dict[str, Any]:
    """Attach reward score; auto-store high-quality grounded replies."""
    if os.environ.get("AUREON_CHAT_REWARD", "1").strip().lower() in ("0", "false", "no"):
        return payload

    reply = str(payload.get("reply", ""))
    if not reply or payload.get("abstained"):
        return payload

    reward = score_chat_reply(user_message, reply)
    payload["reward"] = reward

    reject_template = "I don't know — no grounded corpus match."
    if reward["good"] and not payload.get("abstained"):
        try:
            record_preference(
                context=user_message,
                preferred=reply,
                rejected=reject_template,
            )
            reward["stored_preference"] = True
        except Exception:
            logger.debug("Preference store skipped", exc_info=True)

    return payload
