"""Self-inquiry — Aureon asks itself questions while learning (Socratic inner monologue)."""

from __future__ import annotations

import json
import os
import random
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brain.domains.generate_micros import topics_for
from brain.domains.taxonomy import lookup_names
from brain.grades import get_grade

_batch_lock = threading.Lock()
_batch_inquiry_count = 0
_batch_inquiry_limit: int | None = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int = 100) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, min(maximum, int(raw)))
    except ValueError:
        return default


def is_self_inquiry_enabled() -> bool:
    if _env_bool("AUREON_SELF_INQUIRY", default=False):
        return True
    if os.environ.get("AUREON_SELF_INQUIRY", "").strip().lower() in ("0", "false", "no", "off"):
        return False
    try:
        from app.startup import is_railway

        return is_railway()
    except ImportError:
        return False


def questions_per_target() -> int:
    return _env_int("AUREON_SELF_INQUIRY_QUESTIONS_PER_TARGET", 2, minimum=1, maximum=5)


def max_per_batch() -> int:
    return _env_int("AUREON_SELF_INQUIRY_MAX_PER_BATCH", 25, minimum=5, maximum=200)


def reset_batch_inquiry_budget(limit: int | None = None) -> None:
    global _batch_inquiry_count, _batch_inquiry_limit
    with _batch_lock:
        _batch_inquiry_count = 0
        _batch_inquiry_limit = limit if limit is not None else max_per_batch()


def _take_batch_slot() -> bool:
    global _batch_inquiry_count
    with _batch_lock:
        limit = _batch_inquiry_limit if _batch_inquiry_limit is not None else max_per_batch()
        if _batch_inquiry_count >= limit:
            return False
        _batch_inquiry_count += 1
        return True


def inquiry_log_path() -> Path:
    data_dir = os.environ.get("AUREON_DATA_DIR", "data").strip() or "data"
    path = Path(data_dir) / "self_inquiry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append_inquiry(record: dict[str, Any]) -> None:
    line = {**record, "ts": datetime.now(timezone.utc).isoformat()}
    path = inquiry_log_path()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, default=str) + "\n")


def recent_inquiries(limit: int = 20) -> list[dict[str, Any]]:
    path = inquiry_log_path()
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for raw in reversed(lines[-limit * 2 :]):
        if not raw.strip():
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out


def _question_templates(grade_slug: str) -> list[str]:
    templates: dict[str, list[str]] = {
        "preschool": [
            "What is {micro_display}?",
            "What is one word I would use to describe {topic}?",
        ],
        "elementary": [
            "Why does {micro_display} live under {sub_display}?",
            "What did my collector region find about {topic}?",
        ],
        "middle_school": [
            "How does {micro_display} connect to other ideas in {domain_display}?",
            "Did my labels for {topic} make sense this cycle?",
        ],
        "high_school": [
            "What pattern do I notice in {micro_display} after training?",
            "If {topic} were wrong, how would my verifier catch it?",
        ],
        "undergraduate": [
            "What evidence supports what I think I know about {micro_display}?",
            "How confident am I in {topic} at {grade_name} level?",
        ],
        "masters": [
            "What gap remains in my understanding of {micro_display}?",
            "How would I teach {topic} to someone at elementary level?",
        ],
        "doctorate": [
            "What original question about {micro_display} do I still cannot answer?",
            "If I mastered {path}, what should I question next in {domain_display}?",
        ],
    }
    return templates.get(grade_slug, templates["elementary"])


def generate_questions(
    *,
    domain_slug: str,
    subdomain_slug: str,
    micro_slug: str,
    grade_slug: str,
    count: int,
) -> list[str]:
    names = lookup_names(domain_slug, subdomain=subdomain_slug, micro=micro_slug)
    grade = get_grade(grade_slug)
    grade_name = grade.name if grade else grade_slug.replace("_", " ").title()
    leaf_topics = topics_for(domain_slug, subdomain_slug, micro_slug)
    topic = random.choice(leaf_topics) if leaf_topics else names.get("micro_subdomain", micro_slug)

    ctx = {
        "domain_display": names.get("domain", domain_slug),
        "sub_display": names.get("subdomain", subdomain_slug),
        "micro_display": names.get("micro_subdomain", micro_slug),
        "topic": topic,
        "grade_name": grade_name,
        "path": f"{domain_slug}.{subdomain_slug}.{micro_slug}",
    }

    pool = _question_templates(grade_slug)
    random.shuffle(pool)
    chosen = pool[:count]
    return [q.format(**ctx) for q in chosen]


def answer_question(
    question: str,
    *,
    outcome: dict[str, Any],
) -> str:
    """Answer from cycle metrics — inner voice, not an external LLM."""
    graduation = outcome.get("graduation") or {}
    regions = outcome.get("regions") or []
    grade_name = outcome.get("grade_name") or outcome.get("grade", "this grade")
    passed = graduation.get("passed")
    unlocked = graduation.get("unlocked_next")
    train_acc = graduation.get("train_accuracy")

    region_bits: list[str] = []
    for row in regions:
        status = row.get("status", "?")
        region = row.get("region", "?")
        metrics = row.get("metrics") or {}
        if status == "skipped" and metrics.get("reason"):
            region_bits.append(f"{region}: skipped ({metrics['reason']})")
        elif status == "completed":
            region_bits.append(f"{region}: ok")
        else:
            region_bits.append(f"{region}: {status}")

    if passed:
        progress = f"I passed {grade_name}"
        if unlocked:
            progress += f" and unlocked {unlocked.replace('_', ' ')}"
        progress += "."
    else:
        progress = f"I did not pass {grade_name} yet — I need another cycle."

    if train_acc is not None and train_acc > 0:
        progress += f" Training accuracy was {train_acc:.0%}."

    reflection = (
        f"Asking myself: «{question}» — {progress} "
        f"My six regions this cycle: {'; '.join(region_bits) or 'none recorded'}. "
        "Each question I ask builds the map — like a child learning to think by wondering aloud."
    )
    return reflection


def run_self_inquiry_for_cycle(outcome: dict[str, Any], *, source: str = "auto_learn") -> list[dict[str, Any]]:
    """After a grade cycle, ask and answer questions about what was just learned."""
    from app.activity_log import log_ai_activity

    if not is_self_inquiry_enabled():
        return []
    if outcome.get("error") or outcome.get("fully_graduated"):
        return []
    if not _take_batch_slot():
        return []

    domain = outcome["domain"]
    subdomain = outcome["subdomain"]
    micro = outcome["micro_subdomain"]
    grade = outcome.get("grade") or "preschool"
    path = f"{domain}.{subdomain}.{micro}"

    exchanges: list[dict[str, Any]] = []
    for question in generate_questions(
        domain_slug=domain,
        subdomain_slug=subdomain,
        micro_slug=micro,
        grade_slug=grade,
        count=questions_per_target(),
    ):
        answer = answer_question(question, outcome=outcome)
        record = {
            "question": question,
            "answer": answer,
            "path": path,
            "grade": grade,
            "source": source,
            "graduation_passed": (outcome.get("graduation") or {}).get("passed"),
        }
        append_inquiry(record)
        exchanges.append(record)
        log_ai_activity(
            "self_inquiry",
            source=source,
            path=path,
            grade=grade,
            question=question,
            answer=answer[:500],
        )

    return exchanges
