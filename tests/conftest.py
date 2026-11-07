"""Pytest configuration for Dungeon Master OS."""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DMOS_DATA_DIR", str(tmp_path / "dmos_data"))
    monkeypatch.setenv("DMOS_PROVIDER", "offline")
