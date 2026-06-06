#!/usr/bin/env python3
"""Score file upload modalities — must reach 90% to pass."""

from __future__ import annotations

import io
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app
from brain.file_router import route_bytes
from brain.multimodal_processors import (
    _detect_tables_in_text,
    process_code_file,
    process_csv,
    process_excel,
    tier_status,
)

PASS_THRESHOLD = 0.90
client = TestClient(app)


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ModalityScore:
    modality: str
    checks: list[Check] = field(default_factory=list)

    @property
    def score(self) -> float:
        if not self.checks:
            return 0.0
        return sum(1 for c in self.checks if c.passed) / len(self.checks)


def _minimal_png() -> bytes:
    try:
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (8, 8), color=(40, 120, 200)).save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )


def _minimal_wav() -> bytes:
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 800)
    return buf.getvalue()


def _sample_csv() -> bytes:
    return b"name,score\nAlice,88\nBob,92\nCarol,76\n"


def _sample_xlsx() -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError:
        return b""

    wb = Workbook()
    ws = wb.active
    ws.append(["product", "units", "revenue"])
    ws.append(["widget", 10, 100.0])
    ws.append(["gadget", 5, 75.0])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _sample_python() -> bytes:
    return b"def greet(name):\n    return name\n\nclass Greeter:\n    pass\n"


def _api_upload(filename: str, data: bytes, message: str = "What is in this file?") -> dict:
    files = {"file": (filename, io.BytesIO(data), "application/octet-stream")}
    response = client.post(
        "/api/chat/file",
        data={"message": message, "persist": "false"},
        files=files,
    )
    if response.status_code != 200:
        return {"ok": False, "status": response.status_code, "body": response.text[:200]}
    body = response.json()
    return {"ok": True, "body": body}


def score_pdf() -> ModalityScore:
    ms = ModalityScore("pdf")
    table_text = "Name    Age\nAlice   30\nBob     25"
    ms.checks.append(Check("table_heuristic", "Alice" in _detect_tables_in_text(table_text)))

    routed = route_bytes("doc.pdf", b"%PDF-fake")
    ms.checks.append(Check("routes_without_crash", routed.modality == "pdf"))

    api = _api_upload("report.pdf", b"%PDF-fake")
    if api["ok"]:
        file_info = api["body"].get("file", {})
        ms.checks.append(Check("api_returns_file_block", file_info.get("modality") == "pdf"))
        ms.checks.append(Check("api_returns_reply", len(api["body"].get("reply", "")) > 5))
    else:
        ms.checks.append(Check("api_returns_file_block", False, str(api)))
        ms.checks.append(Check("api_returns_reply", False))

    return ms


def score_text_markdown() -> ModalityScore:
    ms = ModalityScore("text")
    data = b"# Upload Test\n\nMarkdown ingestion body for Aureon."
    routed = route_bytes("readme.md", data, message="Summarize")
    ms.checks.append(Check("modality_text", routed.modality == "text"))
    ms.checks.append(Check("content_preserved", "Markdown ingestion" in routed.text))
    ms.checks.append(Check("user_message_appended", "Summarize" in routed.text))

    api = _api_upload("readme.md", data)
    if api["ok"]:
        ms.checks.append(Check("api_modality", api["body"]["file"]["modality"] == "text"))
        ms.checks.append(Check("api_preview", "Markdown ingestion" in api["body"]["file"]["text_preview"]))
    else:
        ms.checks.append(Check("api_modality", False))
        ms.checks.append(Check("api_preview", False))
    return ms


def score_csv() -> ModalityScore:
    ms = ModalityScore("csv")
    data = _sample_csv()
    text, meta = process_csv(data, "scores.csv")
    ms.checks.append(Check("row_count", "3 data rows" in text))
    ms.checks.append(Check("numeric_mean", meta.get("numeric_stats", {}).get("score", {}).get("mean") == 85.3333))
    ms.checks.append(Check("sample_row", "Alice" in text))

    api = _api_upload("scores.csv", data)
    if api["ok"]:
        ms.checks.append(Check("api_modality", api["body"]["file"]["modality"] == "csv"))
        ms.checks.append(Check("api_has_stats", "mean=" in api["body"]["file"]["text_preview"]))
    else:
        ms.checks.append(Check("api_modality", False))
        ms.checks.append(Check("api_has_stats", False))
    return ms


def score_excel() -> ModalityScore:
    ms = ModalityScore("excel")
    data = _sample_xlsx()
    if not data:
        ms.checks.append(Check("openpyxl_installed", False, "install openpyxl"))
        ms.checks.extend(Check(f"skip_{i}", False) for i in range(4))
        return ms

    ms.checks.append(Check("openpyxl_installed", True))
    text, meta = process_excel(data, "sales.xlsx")
    ms.checks.append(Check("analysis_text", "Excel analysis" in text))
    ms.checks.append(Check("revenue_stats", "revenue" in meta.get("numeric_stats", {})))

    api = _api_upload("sales.xlsx", data)
    if api["ok"]:
        ms.checks.append(Check("api_modality", api["body"]["file"]["modality"] == "excel"))
        ms.checks.append(Check("api_preview", "revenue" in api["body"]["file"]["text_preview"]))
    else:
        ms.checks.append(Check("api_modality", False))
        ms.checks.append(Check("api_preview", False))
    return ms


def score_code() -> ModalityScore:
    ms = ModalityScore("code")
    data = _sample_python()
    text, meta = process_code_file(data, "app.py")
    ms.checks.append(Check("python_ast", meta.get("syntax_valid") is True))
    ms.checks.append(Check("detects_greet", "greet" in meta.get("functions", [])))
    ms.checks.append(Check("detects_class", "Greeter" in meta.get("classes", [])))

    js = b"function add(a,b){return a+b;}"
    _, js_meta = process_code_file(js, "util.js")
    ms.checks.append(Check("javascript_functions", "add" in js_meta.get("functions", [])))

    api = _api_upload("app.py", data)
    if api["ok"]:
        ms.checks.append(Check("api_modality", api["body"]["file"]["modality"] == "code"))
        ms.checks.append(Check("api_preview", "greet" in api["body"]["file"]["text_preview"]))
    else:
        ms.checks.append(Check("api_modality", False))
        ms.checks.append(Check("api_preview", False))
    return ms


def score_image() -> ModalityScore:
    ms = ModalityScore("image")
    data = _minimal_png()
    routed = route_bytes("photo.png", data)
    ms.checks.append(Check("modality_image", routed.modality == "image"))
    ms.checks.append(Check("caption_present", "Image upload" in routed.text))
    ms.checks.append(
        Check(
            "metadata_or_hash",
            bool(routed.metadata.get("width")) or bool(routed.metadata.get("content_hash")),
        )
    )

    api = _api_upload("photo.png", data)
    if api["ok"]:
        ms.checks.append(Check("api_modality", api["body"]["file"]["modality"] == "image"))
        ms.checks.append(Check("api_reply", len(api["body"].get("reply", "")) > 5))
    else:
        ms.checks.append(Check("api_modality", False))
        ms.checks.append(Check("api_reply", False))
    return ms


def score_audio() -> ModalityScore:
    ms = ModalityScore("audio")
    data = _minimal_wav()
    routed = route_bytes("clip.wav", data)
    ms.checks.append(Check("modality_audio", routed.modality == "audio"))
    ms.checks.append(Check("transcript_or_fallback", len(routed.text) > 20))
    ms.checks.append(Check("audio_tier_meta", "audio_tier" in routed.metadata))

    api = _api_upload("clip.wav", data)
    if api["ok"]:
        ms.checks.append(Check("api_modality", api["body"]["file"]["modality"] == "audio"))
        ms.checks.append(Check("api_reply", len(api["body"].get("reply", "")) > 5))
    else:
        ms.checks.append(Check("api_modality", False))
        ms.checks.append(Check("api_reply", False))
    return ms


def score_tiers() -> ModalityScore:
    ms = ModalityScore("infrastructure")
    status = tier_status()
    for key in ("pdf", "vision", "audio", "csv", "excel", "code"):
        ms.checks.append(Check(f"tier_{key}", key in status and status[key] not in (None, "")))
    ms.checks.append(Check("multimodal_status_api", client.get("/api/brain/multimodal/status").status_code == 200))
    return ms


def main() -> int:
    sections = [
        score_pdf(),
        score_text_markdown(),
        score_csv(),
        score_excel(),
        score_code(),
        score_image(),
        score_audio(),
        score_tiers(),
    ]

    total_checks = 0
    passed_checks = 0
    report: list[dict] = []

    print(f"File upload score report (pass threshold: {PASS_THRESHOLD:.0%})\n")
    for section in sections:
        pct = section.score * 100
        mark = "PASS" if section.score >= PASS_THRESHOLD else "FAIL"
        print(f"[{mark}] {section.modality}: {pct:.1f}% ({sum(c.passed for c in section.checks)}/{len(section.checks)})")
        for check in section.checks:
            status = "ok" if check.passed else "FAIL"
            suffix = f" — {check.detail}" if check.detail and not check.passed else ""
            print(f"  [{status}] {check.name}{suffix}")
        total_checks += len(section.checks)
        passed_checks += sum(1 for c in section.checks if c.passed)
        report.append(
            {
                "modality": section.modality,
                "score": round(section.score, 4),
                "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in section.checks],
            }
        )

    overall = passed_checks / total_checks if total_checks else 0.0
    print(f"\n{'=' * 60}")
    print(f"Overall: {passed_checks}/{total_checks} checks = {overall:.1%}")
    print(f"Threshold: {PASS_THRESHOLD:.0%} — {'PASSED' if overall >= PASS_THRESHOLD else 'FAILED'}")

    out = ROOT / "data" / "audit" / "file-upload-score.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "overall_score": round(overall, 4),
                "passed": overall >= PASS_THRESHOLD,
                "threshold": PASS_THRESHOLD,
                "sections": report,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out}")

    return 0 if overall >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
