"""Grade progression — unlock, graduate, and track academic levels per micro-subdomain."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from brain.grades import (
    GRADE_CURRICULUM,
    GradeLevel,
    first_grade,
    get_grade,
    grade_to_dict,
    next_grade,
)
from db.models import GradeProgress, KnowledgeMicroSubdomain


def seed_grade_progress(session: Session) -> int:
    """Create grade rows for every micro-subdomain — preschool unlocked, rest locked."""
    created = 0
    micros = session.scalars(select(KnowledgeMicroSubdomain)).all()
    entry = first_grade()
    for micro in micros:
        for grade in GRADE_CURRICULUM:
            exists = session.scalar(
                select(GradeProgress).where(
                    GradeProgress.micro_subdomain_id == micro.id,
                    GradeProgress.grade_slug == grade.slug,
                )
            )
            if exists:
                continue
            status = "unlocked" if grade.slug == entry.slug else "locked"
            session.add(
                GradeProgress(
                    domain_id=micro.domain_id,
                    subdomain_id=micro.subdomain_id,
                    micro_subdomain_id=micro.id,
                    grade_slug=grade.slug,
                    grade_order=grade.order,
                    status=status,
                )
            )
            created += 1
    session.flush()
    return created


def _progress_rows(session: Session, micro_subdomain_id: int) -> list[GradeProgress]:
    return list(
        session.scalars(
            select(GradeProgress)
            .where(GradeProgress.micro_subdomain_id == micro_subdomain_id)
            .order_by(GradeProgress.grade_order)
        ).all()
    )


def is_grade_unlocked(session: Session, micro_subdomain_id: int, grade_slug: str) -> bool:
    row = session.scalar(
        select(GradeProgress).where(
            GradeProgress.micro_subdomain_id == micro_subdomain_id,
            GradeProgress.grade_slug == grade_slug,
        )
    )
    return row is not None and row.status in ("unlocked", "in_progress", "graduated", "failed")


def current_grade(session: Session, micro_subdomain_id: int) -> GradeProgress | None:
    """Lowest-order grade that is unlocked but not yet graduated."""
    for row in _progress_rows(session, micro_subdomain_id):
        if row.status == "graduated":
            continue
        if row.status in ("unlocked", "in_progress", "failed"):
            return row
    return None


def require_grade_unlocked(session: Session, micro_subdomain_id: int, grade_slug: str) -> GradeLevel:
    grade = get_grade(grade_slug)
    if not grade:
        raise ValueError(f"Unknown grade: {grade_slug}")
    if not is_grade_unlocked(session, micro_subdomain_id, grade_slug):
        raise ValueError(
            f"Grade {grade_slug} is locked — graduate the previous level first."
        )
    return grade


def mark_grade_in_progress(session: Session, micro_subdomain_id: int, grade_slug: str) -> None:
    row = session.scalar(
        select(GradeProgress).where(
            GradeProgress.micro_subdomain_id == micro_subdomain_id,
            GradeProgress.grade_slug == grade_slug,
        )
    )
    if row and row.status in ("unlocked", "failed"):
        row.status = "in_progress"
        row.attempts += 1
        row.last_attempt_at = datetime.now(timezone.utc)


def process_graduation(
    session: Session,
    micro_subdomain_id: int,
    grade_slug: str,
    *,
    trainer_metrics: dict[str, Any],
    evaluator_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Decide pass/fail for a grade and unlock the next level on success."""
    grade = get_grade(grade_slug)
    if not grade:
        return {"error": f"unknown grade {grade_slug}"}

    row = session.scalar(
        select(GradeProgress).where(
            GradeProgress.micro_subdomain_id == micro_subdomain_id,
            GradeProgress.grade_slug == grade_slug,
        )
    )
    if not row:
        return {"error": "grade progress not found"}

    train_acc = float(trainer_metrics.get("train_accuracy", 0.0))
    trainer_status = str(trainer_metrics.get("status", ""))
    evaluator_status = str(evaluator_metrics.get("status", ""))

    if trainer_status == "skipped" and grade.order <= 2:
        trainer_ok = True
    elif trainer_status == "completed":
        trainer_ok = train_acc >= grade.min_train_accuracy
    else:
        trainer_ok = False

    if evaluator_status == "skipped":
        gates_ok = grade.order <= 2
    else:
        gates_ok = bool(evaluator_metrics.get("all_passed", False))

    passed = trainer_ok and gates_ok

    row.metrics = {
        "train_accuracy": train_acc,
        "evaluator": evaluator_metrics,
        "trainer_status": trainer_metrics.get("status"),
    }
    row.last_attempt_at = datetime.now(timezone.utc)

    result: dict[str, Any] = {
        "grade": grade_slug,
        "passed": passed,
        "train_accuracy": train_acc,
        "min_train_accuracy": grade.min_train_accuracy,
        "evaluator_passed": gates_ok,
    }

    if passed:
        row.status = "graduated"
        row.graduated_at = datetime.now(timezone.utc)
        nxt = next_grade(grade_slug)
        if nxt:
            next_row = session.scalar(
                select(GradeProgress).where(
                    GradeProgress.micro_subdomain_id == micro_subdomain_id,
                    GradeProgress.grade_slug == nxt.slug,
                )
            )
            if next_row and next_row.status == "locked":
                next_row.status = "unlocked"
            result["unlocked_next"] = nxt.slug
        else:
            result["fully_graduated"] = True
    else:
        row.status = "failed"
        result["retry_allowed"] = True

    session.flush()
    return result


def progress_report(session: Session, micro_subdomain_id: int) -> dict[str, Any]:
    rows = _progress_rows(session, micro_subdomain_id)
    current = current_grade(session, micro_subdomain_id)
    graduated = sum(1 for r in rows if r.status == "graduated")
    return {
        "micro_subdomain_id": micro_subdomain_id,
        "current_grade": current.grade_slug if current else None,
        "grades_graduated": graduated,
        "total_grades": len(GRADE_CURRICULUM),
        "fully_graduated": graduated >= len(GRADE_CURRICULUM),
        "grades": [
            {
                "slug": r.grade_slug,
                "order": r.grade_order,
                "status": r.status,
                "attempts": r.attempts,
                "graduated_at": r.graduated_at.isoformat() if r.graduated_at else None,
                "metrics": r.metrics,
                "curriculum": grade_to_dict(g) if (g := get_grade(r.grade_slug)) else None,
            }
            for r in rows
        ],
    }
