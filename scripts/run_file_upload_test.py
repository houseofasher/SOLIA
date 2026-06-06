#!/usr/bin/env python3
"""Run file upload modality tests through Aureon file_router and /api/chat/file."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

if __name__ == "__main__":
    raise SystemExit(pytest.main([str(ROOT / "tests" / "test_file_upload_suite.py"), "-v", "--tb=short"]))
