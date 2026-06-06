"""Tier 3–4 multimodal processors — PDF, CLIP-style vision, Whisper-style audio."""

from __future__ import annotations

import ast
import csv
import hashlib
import io
import logging
import os
import re
import statistics
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
PDF_EXT = {".pdf"}
TEXT_EXT = {".txt", ".md", ".json", ".jsonl"}
CSV_EXT = {".csv"}
EXCEL_EXT = {".xlsx", ".xls"}
CODE_EXT = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".cs",
    ".rb",
}


def tier_status() -> dict[str, Any]:
    return {
        "pdf": _pdf_available(),
        "vision": _vision_tier(),
        "audio": _whisper_tier(),
        "csv": "stdlib",
        "excel": _excel_tier(),
        "code": "ast_and_structure",
        "pgvector": os.environ.get("AUREON_PGVECTOR", "1").strip().lower() not in ("0", "false", "no"),
    }


def _pdf_available() -> bool:
    try:
        import pypdf  # noqa: F401

        return True
    except ImportError:
        return False


def _vision_tier() -> str:
    if os.environ.get("AUREON_CLIP", "1").strip().lower() in ("0", "false", "no"):
        return "disabled"
    try:
        from PIL import Image  # noqa: F401

        return "pil_metadata"
    except ImportError:
        return "hash_fingerprint"


def _whisper_tier() -> str:
    if os.environ.get("AUREON_WHISPER", "1").strip().lower() in ("0", "false", "no"):
        return "disabled"
    try:
        import whisper  # noqa: F401

        return "openai_whisper"
    except ImportError:
        return "sidecar_required"


def _excel_tier() -> str:
    try:
        import openpyxl  # noqa: F401

        return "openpyxl"
    except ImportError:
        return "unavailable"


def extract_pdf(data: bytes) -> str:
    text = _extract_pdf_text(data)
    if not text:
        return ""
    tables = _detect_tables_in_text(text)
    if tables:
        return f"{text}\n\nExtracted table-like rows:\n{tables}"
    return text


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except ImportError:
        return ""
    except Exception as exc:
        logger.warning("PDF extract failed: %s", exc)
        return ""


def _detect_tables_in_text(text: str) -> str:
    """Heuristic table extraction from PDF text lines (pipes or column gaps)."""
    rows: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 4:
            continue
        if stripped.count("|") >= 2:
            rows.append(stripped)
            continue
        cells = [c.strip() for c in re.split(r"\s{2,}", line) if c.strip()]
        if len(cells) >= 2:
            rows.append(" | ".join(cells))
    return "\n".join(rows[:40])


def process_image(data: bytes, filename: str) -> tuple[str, dict[str, Any]]:
    """Tier 3 vision — PIL metadata + hash fingerprint; Tier 4 CLIP when installed."""
    meta: dict[str, Any] = {"modality": "image", "filename": filename, "bytes": len(data)}
    caption_parts: list[str] = [f"Image upload: {filename}"]

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        meta.update({"width": img.width, "height": img.height, "format": img.format or "unknown"})
        caption_parts.append(f"{img.width}x{img.height} {img.format or 'image'}")
        if hasattr(img, "getcolors") and img.width * img.height < 250_000:
            colors = img.convert("RGB").getcolors(maxcolors=256)
            if colors:
                dominant = max(colors, key=lambda c: c[0])
                meta["dominant_rgb"] = dominant[1]
    except ImportError:
        meta["vision_tier"] = "hash_fingerprint"
    except Exception as exc:
        meta["vision_error"] = str(exc)[:120]

    digest = hashlib.sha256(data).hexdigest()
    meta["content_hash"] = digest
    caption_parts.append(f"sha256={digest[:16]}")

    clip_caption = _try_clip_caption(data)
    if clip_caption:
        meta["vision_tier"] = "clip"
        caption_parts.append(clip_caption)

    return " ".join(caption_parts), meta


def _try_clip_caption(data: bytes) -> str | None:
    """Optional CLIP — only when torch + transformers available."""
    if os.environ.get("AUREON_CLIP", "1").strip().lower() in ("0", "false", "no"):
        return None
    try:
        import torch
        from PIL import Image
        from transformers import CLIPModel, CLIPProcessor

        labels = [
            "a diagram or chart",
            "a photograph of a person",
            "a screenshot of software code",
            "a medical scan",
            "a natural landscape",
            "a document or text page",
        ]
        model_name = os.environ.get("AUREON_CLIP_MODEL", "openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained(model_name)
        model = CLIPModel.from_pretrained(model_name)
        img = Image.open(io.BytesIO(data)).convert("RGB")
        inputs = processor(text=labels, images=img, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0]
        best = int(probs.argmax())
        return f"CLIP classification: {labels[best]} ({float(probs[best]):.0%})"
    except Exception:
        return None


def process_audio(data: bytes, filename: str) -> tuple[str, dict[str, Any]]:
    """Tier 3 sidecar; Tier 4 Whisper when openai-whisper installed."""
    meta: dict[str, Any] = {"modality": "audio", "filename": filename, "bytes": len(data)}
    transcript = _try_whisper_transcribe(data, filename)
    if transcript:
        meta["audio_tier"] = "whisper"
        return transcript.strip(), meta
    meta["audio_tier"] = "pending_transcript"
    return (
        f"Audio upload {filename} ({len(data)} bytes) — transcript pending. "
        f"Install openai-whisper or add a .txt sidecar with transcript.",
        meta,
    )


def _try_whisper_transcribe(data: bytes, filename: str) -> str | None:
    if os.environ.get("AUREON_WHISPER", "1").strip().lower() in ("0", "false", "no"):
        return None
    try:
        import tempfile
        import whisper

        model_size = os.environ.get("AUREON_WHISPER_MODEL", "base")
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        model = whisper.load_model(model_size)
        result = model.transcribe(tmp_path)
        os.unlink(tmp_path)
        return str(result.get("text", "")).strip() or None
    except Exception as exc:
        logger.debug("Whisper unavailable: %s", exc)
        return None


def extract_text_file(data: bytes, filename: str) -> str:
    try:
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def process_csv(data: bytes, filename: str) -> tuple[str, dict[str, Any]]:
    """Parse CSV and summarize numeric columns."""
    raw = data.decode("utf-8-sig", errors="ignore")
    reader = csv.reader(io.StringIO(raw))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return f"CSV {filename} is empty.", {"modality": "csv", "rows": 0}

    header = [cell.strip() for cell in rows[0]]
    data_rows = rows[1:] if len(rows) > 1 else []
    numeric_stats: dict[str, dict[str, float | int]] = {}

    for col_idx, col_name in enumerate(header):
        values: list[float] = []
        for row in data_rows:
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip()
            if not cell:
                continue
            try:
                values.append(float(cell))
            except ValueError:
                continue
        if values:
            numeric_stats[col_name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": round(statistics.mean(values), 4),
            }

    lines = [
        f"CSV analysis for {filename}: {len(data_rows)} data rows, {len(header)} columns.",
        f"Columns: {', '.join(header)}",
    ]
    if data_rows:
        lines.append(f"Sample row: {', '.join(data_rows[0])}")
    for col, stats in numeric_stats.items():
        lines.append(
            f"{col}: count={stats['count']}, min={stats['min']}, max={stats['max']}, mean={stats['mean']}"
        )

    meta: dict[str, Any] = {
        "modality": "csv",
        "rows": len(data_rows),
        "columns": header,
        "numeric_stats": numeric_stats,
    }
    return "\n".join(lines), meta


def process_excel(data: bytes, filename: str) -> tuple[str, dict[str, Any]]:
    """Spreadsheet statistical summary via openpyxl."""
    try:
        import openpyxl
    except ImportError:
        return (
            f"Excel file {filename} uploaded — install openpyxl for spreadsheet analysis.",
            {"modality": "excel", "error": "openpyxl_missing"},
        )

    if filename.lower().endswith(".xls"):
        return (
            f"Legacy .xls file {filename} — convert to .xlsx for full statistical analysis.",
            {"modality": "excel", "format": "xls", "error": "legacy_format"},
        )

    try:
        workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        sheet = workbook.active
        rows = []
        for row in sheet.iter_rows(values_only=True):
            if row and any(cell is not None and str(cell).strip() for cell in row):
                rows.append(["" if cell is None else str(cell).strip() for cell in row])
        workbook.close()
    except Exception as exc:
        return f"Excel file {filename} could not be parsed: {exc}", {"modality": "excel", "error": str(exc)[:120]}

    if not rows:
        return f"Excel file {filename} is empty.", {"modality": "excel", "rows": 0}

    header = rows[0]
    data_rows = rows[1:] if len(rows) > 1 else []
    numeric_stats: dict[str, dict[str, float | int]] = {}
    for col_idx, col_name in enumerate(header):
        values: list[float] = []
        for row in data_rows:
            if col_idx >= len(row):
                continue
            try:
                values.append(float(row[col_idx]))
            except (ValueError, TypeError):
                continue
        if values:
            numeric_stats[col_name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": round(statistics.mean(values), 4),
            }

    lines = [
        f"Excel analysis for {filename}: {len(data_rows)} data rows, {len(header)} columns.",
        f"Columns: {', '.join(header)}",
    ]
    if data_rows:
        lines.append(f"Sample row: {', '.join(data_rows[0])}")
    for col, stats in numeric_stats.items():
        lines.append(
            f"{col}: count={stats['count']}, min={stats['min']}, max={stats['max']}, mean={stats['mean']}"
        )

    return "\n".join(lines), {
        "modality": "excel",
        "rows": len(data_rows),
        "columns": header,
        "numeric_stats": numeric_stats,
    }


def process_code_file(data: bytes, filename: str) -> tuple[str, dict[str, Any]]:
    """Extract structure from source code — Python AST, regex for other languages."""
    source = data.decode("utf-8", errors="ignore")
    ext = Path(filename).suffix.lower()
    meta: dict[str, Any] = {
        "modality": "code",
        "extension": ext,
        "lines": source.count("\n") + 1,
        "bytes": len(data),
    }

    if ext == ".py":
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return f"Python file {filename} has syntax error: {exc}", {**meta, "syntax_valid": False}

        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        meta.update(
            {
                "syntax_valid": True,
                "functions": functions,
                "classes": classes,
                "imports": imports[:20],
            }
        )
        text = (
            f"Python code file {filename}: {len(functions)} function(s) "
            f"[{', '.join(functions) or 'none'}], {len(classes)} class(es) "
            f"[{', '.join(classes) or 'none'}]."
        )
        if imports:
            text += f" Imports: {', '.join(imports[:8])}."
        return text, meta

    if ext in {".js", ".ts", ".jsx", ".tsx"}:
        functions = re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)", source)
        functions += re.findall(
            r"(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(",
            source,
        )
        classes = re.findall(r"class\s+([A-Za-z_][A-Za-z0-9_]*)", source)
        meta.update({"functions": functions, "classes": classes})
        return (
            f"JavaScript/TypeScript file {filename}: functions [{', '.join(functions) or 'none'}], "
            f"classes [{', '.join(classes) or 'none'}].",
            meta,
        )

    if ext == ".java":
        classes = re.findall(r"class\s+([A-Za-z_][A-Za-z0-9_]*)", source)
        methods = re.findall(
            r"(?:public|private|protected)[^{;]+?\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            source,
        )
        meta.update({"classes": classes, "methods": methods[:30]})
        return (
            f"Java file {filename}: classes [{', '.join(classes) or 'none'}], "
            f"methods [{', '.join(methods[:10]) or 'none'}].",
            meta,
        )

    if ext == ".go":
        functions = re.findall(r"func\s+(?:\([^)]+\)\s+)?([A-Za-z_][A-Za-z0-9_]*)", source)
        meta.update({"functions": functions})
        return f"Go file {filename}: functions [{', '.join(functions) or 'none'}].", meta

    if ext == ".rs":
        functions = re.findall(r"fn\s+([A-Za-z_][A-Za-z0-9_]*)", source)
        structs = re.findall(r"struct\s+([A-Za-z_][A-Za-z0-9_]*)", source)
        meta.update({"functions": functions, "structs": structs})
        return (
            f"Rust file {filename}: functions [{', '.join(functions) or 'none'}], "
            f"structs [{', '.join(structs) or 'none'}].",
            meta,
        )

    if ext in {".cpp", ".c", ".h"}:
        functions = re.findall(
            r"(?:int|void|bool|double|float|auto|std::\w+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            source,
        )
        meta.update({"functions": functions[:30]})
        return f"C/C++ file {filename}: functions [{', '.join(functions[:10]) or 'none'}].", meta

    meta["note"] = "generic_code"
    preview = "\n".join(source.splitlines()[:12])
    return f"Code file {filename} ({len(data)} bytes):\n{preview}", meta


def text_embedding(text: str, *, dims: int = 128) -> list[float]:
    """Lightweight embedding for pgvector-style similarity (no external model required)."""
    vec = [0.0] * dims
    tokens = text.lower().split()
    if not tokens:
        return vec
    for tok in tokens:
        h = hashlib.sha256(tok.encode()).digest()
        for i in range(min(8, dims)):
            idx = (h[i] + h[i + 8]) % dims
            vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [round(v / norm, 6) for v in vec]
