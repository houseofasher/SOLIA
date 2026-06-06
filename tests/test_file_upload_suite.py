"""Comprehensive file upload tests — all modalities via file_router and API."""

from __future__ import annotations

import io
import struct
import wave

import pytest
from fastapi.testclient import TestClient

from app.main import app
from brain.file_router import ingest_upload, route_bytes
from brain.multimodal_processors import (
    _detect_tables_in_text,
    process_code_file,
    process_csv,
    process_excel,
    tier_status,
)

client = TestClient(app)


def _minimal_png() -> bytes:
    try:
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (8, 8), color=(40, 120, 200)).save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # 1x1 PNG fallback
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )


def _minimal_wav() -> bytes:
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
    openpyxl = pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["product", "units", "revenue"])
    ws.append(["widget", 10, 100.0])
    ws.append(["gadget", 5, 75.0])
    ws.append(["widget", 3, 30.0])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _sample_python() -> bytes:
    return b"""
import os

def greet(name: str) -> str:
    return f"Hello, {name}"

class Greeter:
    def hello(self):
        return "hi"
""".strip()


def test_tier_status_includes_all_modalities():
    status = tier_status()
    for key in ("pdf", "vision", "audio", "csv", "excel", "code", "pgvector"):
        assert key in status


def test_pdf_table_detection_heuristic():
    text = "Name    Age    City\nAlice   30     NYC\nBob     25     LA"
    tables = _detect_tables_in_text(text)
    assert "Alice" in tables
    assert "Name" in tables or "Age" in tables


def test_route_pdf(monkeypatch):
    monkeypatch.setattr(
        "brain.file_router.extract_pdf",
        lambda _data: "Report title\nName | Score\nAlice | 88",
    )
    result = route_bytes("report.pdf", b"%PDF-fake", message="Summarize tables")
    assert result.modality == "pdf"
    assert "Alice" in result.text
    assert "Summarize tables" in result.text


def test_route_markdown():
    data = b"# Aureon Upload Test\n\nThis markdown file describes multimodal ingestion."
    result = route_bytes("readme.md", data, message="What is this about?")
    assert result.modality == "text"
    assert "Aureon Upload Test" in result.text


def test_route_csv_statistics():
    text, meta = process_csv(_sample_csv(), "scores.csv")
    assert "3 data rows" in text
    assert meta["numeric_stats"]["score"]["mean"] == pytest.approx(85.3333, rel=1e-3)


def test_route_excel_statistics():
    data = _sample_xlsx()
    text, meta = process_excel(data, "sales.xlsx")
    assert "Excel analysis" in text
    assert meta["rows"] == 3
    assert "revenue" in meta["numeric_stats"]


def test_route_code_ast_python():
    text, meta = process_code_file(_sample_python(), "greeter.py")
    assert meta["syntax_valid"] is True
    assert "greet" in meta["functions"]
    assert "Greeter" in meta["classes"]


def test_route_code_javascript():
    source = b"function add(a,b){return a+b;}\nclass Calc { mul(x,y){return x*y;} }"
    text, meta = process_code_file(source, "calc.js")
    assert "add" in meta["functions"]
    assert "Calc" in meta["classes"]


def test_route_image_metadata():
    result = route_bytes("photo.png", _minimal_png(), message="Describe this image")
    assert result.modality == "image"
    assert "Image upload" in result.text
    assert result.metadata.get("width") or result.metadata.get("content_hash")


def test_route_audio_fallback_without_whisper():
    result = route_bytes("clip.wav", _minimal_wav(), message="Transcribe this")
    assert result.modality == "audio"
    assert "Audio upload" in result.text or "transcript" in result.text.lower()


def test_ingest_upload_persists_code_file():
    result = ingest_upload("module.py", _sample_python(), persist=False)
    assert result.modality == "code"
    assert "greet" in result.text


@pytest.mark.parametrize(
    ("filename", "data_fn", "modality", "needle"),
    [
        ("notes.md", lambda: b"# Doc\n\nMarkdown body for upload test.", "text", "Markdown body"),
        ("scores.csv", _sample_csv, "csv", "Alice"),
        ("sales.xlsx", _sample_xlsx, "excel", "revenue"),
        ("app.py", _sample_python, "code", "greet"),
        ("pic.png", _minimal_png, "image", "Image upload"),
        ("voice.wav", _minimal_wav, "audio", "Audio upload"),
    ],
)
def test_api_chat_file_upload(filename, data_fn, modality, needle):
    data = data_fn() if callable(data_fn) else data_fn
    files = {"file": (filename, io.BytesIO(data), "application/octet-stream")}
    payload = {"message": "What is in this file?", "persist": "false"}
    response = client.post("/api/chat/file", data=payload, files=files)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["file"]["modality"] == modality
    assert needle in body["file"]["text_preview"]
    assert "reply" in body
    assert len(body["reply"]) > 5


def test_api_chat_file_pdf(monkeypatch):
    monkeypatch.setattr(
        "brain.file_router.extract_pdf",
        lambda _data: "Quarterly revenue was 1.2M with strong growth in widgets.",
    )
    files = {"file": ("q1.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
    response = client.post(
        "/api/chat/file",
        data={"message": "What were revenues?", "persist": "false"},
        files=files,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["file"]["modality"] == "pdf"
    assert "1.2M" in body["file"]["text_preview"]
