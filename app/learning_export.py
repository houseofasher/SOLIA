"""Export Aureon learning state as JSON files safe for public GitHub sync."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auto_learn import get_auto_learn_scheduler, load_target_cursor
from app.chat_service import learning_snapshot
from brain.self_inquiry import inquiry_log_path
from db.models import (
    Document,
    DocumentLabel,
    GradeProgress,
    KnowledgeDomain,
    KnowledgeMicroSubdomain,
    KnowledgeSubdomain,
    TrainingRun,
)
from db.session import get_session

CORPUS_PREFIX = "learning-corpus"
MAX_DOCUMENTS = int(os.environ.get("AUREON_GITHUB_SYNC_MAX_DOCS", "5000"))
INCLUDE_TEXT = os.environ.get("AUREON_GITHUB_SYNC_INCLUDE_TEXT", "1").strip().lower() in (
    "1",
    "true",
    "yes",
)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _grade_progress_rows(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            GradeProgress,
            KnowledgeDomain.slug,
            KnowledgeSubdomain.slug,
            KnowledgeMicroSubdomain.slug,
            KnowledgeMicroSubdomain.name,
        )
        .join(KnowledgeDomain, GradeProgress.domain_id == KnowledgeDomain.id)
        .join(KnowledgeSubdomain, GradeProgress.subdomain_id == KnowledgeSubdomain.id)
        .join(KnowledgeMicroSubdomain, GradeProgress.micro_subdomain_id == KnowledgeMicroSubdomain.id)
        .order_by(GradeProgress.micro_subdomain_id, GradeProgress.grade_order)
    ).all()

    out: list[dict[str, Any]] = []
    for progress, domain_slug, sub_slug, micro_slug, micro_name in rows:
        if progress.status not in ("graduated", "in_progress", "failed", "unlocked"):
            continue
        out.append(
            {
                "path": f"{domain_slug}.{sub_slug}.{micro_slug}",
                "micro_name": micro_name,
                "grade": progress.grade_slug,
                "status": progress.status,
                "attempts": progress.attempts,
                "metrics": progress.metrics,
                "graduated_at": _iso(progress.graduated_at),
                "last_attempt_at": _iso(progress.last_attempt_at),
            }
        )
    return out


def _documents_index(session: Session) -> list[dict[str, Any]]:
    docs = session.scalars(
        select(Document).order_by(Document.id.desc()).limit(MAX_DOCUMENTS)
    ).all()
    rows: list[dict[str, Any]] = []
    for doc in docs:
        extra = doc.extra or {}
        row: dict[str, Any] = {
            "id": doc.id,
            "source": doc.source,
            "title": doc.title,
            "url": doc.url,
            "language": doc.language,
            "verified": doc.verified,
            "quality_score": doc.quality_score,
            "topic": extra.get("topic"),
            "domain": extra.get("domain"),
            "subdomain": extra.get("subdomain"),
            "micro_subdomain": extra.get("micro_subdomain"),
            "grade": extra.get("grade"),
            "created_at": _iso(doc.created_at),
        }
        if INCLUDE_TEXT:
            row["text"] = doc.text[:4000] if len(doc.text) > 4000 else doc.text
        rows.append(row)
    return list(reversed(rows))


def _training_runs(session: Session) -> list[dict[str, Any]]:
    runs = session.scalars(select(TrainingRun).order_by(TrainingRun.id.desc()).limit(500)).all()
    return [
        {
            "run_id": run.run_id,
            "domain_id": run.domain_id,
            "subdomain_id": run.subdomain_id,
            "metrics": run.metrics,
            "artifact_path": run.artifact_path,
            "params": run.params,
            "promoted": run.promoted,
            "created_at": _iso(run.created_at),
        }
        for run in runs
    ]


def _label_stats(session: Session) -> dict[str, int]:
    total = session.scalar(select(func.count()).select_from(DocumentLabel)) or 0
    review = session.scalar(
        select(func.count()).select_from(DocumentLabel).where(DocumentLabel.needs_review.is_(True))
    ) or 0
    return {"labels_total": total, "labels_needs_review": review}


def build_export_files() -> dict[str, bytes]:
    """Build path → UTF-8 file bytes under learning-corpus/."""
    exported_at = datetime.now(timezone.utc).isoformat()
    snapshot = learning_snapshot()
    snapshot["exported_at"] = exported_at
    snapshot["github_sync"] = {
        "batch_cursor": load_target_cursor(),
        "include_document_text": INCLUDE_TEXT,
        "max_documents": MAX_DOCUMENTS,
    }

    with get_session() as session:
        grade_progress = _grade_progress_rows(session)
        documents = _documents_index(session)
        training_runs = _training_runs(session)
        label_stats = _label_stats(session)

    graduated = sum(1 for g in grade_progress if g["status"] == "graduated")
    in_progress = sum(1 for g in grade_progress if g["status"] == "in_progress")

    readme = "\n".join(
        [
            "# Aureon learning corpus (auto-synced)",
            "",
            f"**Exported:** {exported_at}",
            "",
            "## Summary",
            "",
            f"- Documents indexed: **{len(documents)}**",
            f"- Grade progress rows: **{len(grade_progress)}**",
            f"- Graduated grade steps: **{graduated}**",
            f"- In progress: **{in_progress}**",
            f"- Training runs: **{len(training_runs)}**",
            f"- Labels: **{label_stats['labels_total']}** ({label_stats['labels_needs_review']} need review)",
            "",
            "Auto-generated by Aureon on Railway — do not edit by hand.",
            "Secrets, API keys, and audit logs are never included.",
            "",
        ]
    )

    files: dict[str, bytes] = {
        f"{CORPUS_PREFIX}/README.md": readme.encode("utf-8"),
        f"{CORPUS_PREFIX}/snapshot.json": json.dumps(snapshot, indent=2, ensure_ascii=False).encode(
            "utf-8"
        ),
        f"{CORPUS_PREFIX}/grade_progress.json": json.dumps(
            grade_progress, indent=2, ensure_ascii=False
        ).encode("utf-8"),
        f"{CORPUS_PREFIX}/documents_index.json": json.dumps(
            documents, indent=2, ensure_ascii=False
        ).encode("utf-8"),
        f"{CORPUS_PREFIX}/training_runs.json": json.dumps(
            training_runs, indent=2, ensure_ascii=False
        ).encode("utf-8"),
        f"{CORPUS_PREFIX}/label_stats.json": json.dumps(label_stats, indent=2).encode("utf-8"),
    }

    inquiry_path = inquiry_log_path()
    if inquiry_path.is_file():
        files[f"{CORPUS_PREFIX}/self_inquiry.jsonl"] = inquiry_path.read_bytes()

    return files


def write_local_export(base_dir: Path | None = None) -> Path:
    """Write export files under AUREON_DATA_DIR/learning-corpus for inspection."""
    data_dir = base_dir or Path(os.environ.get("AUREON_DATA_DIR", "data").strip() or "data")
    out_dir = data_dir / CORPUS_PREFIX
    out_dir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in build_export_files().items():
        target = data_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return out_dir
