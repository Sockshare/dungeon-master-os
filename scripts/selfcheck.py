#!/usr/bin/env python3
"""Dungeon Master OS setup, math & health self-check script.

    python scripts/selfcheck.py [--server http://127.0.0.1:8093]
"""

from __future__ import annotations

import argparse
import importlib
import os
import site
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_VENV_SP = ROOT / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if _VENV_SP.is_dir() and str(_VENV_SP) not in sys.path:
    site.addsitedir(str(_VENV_SP))

OK, BAD, WARN = "✅", "❌", "⚠️ "


def line(status: str, text: str, fix: str = "") -> None:
    print(f"{status} {text}")
    if fix:
        print(f"      → {fix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dungeon Master OS self-check")
    parser.add_argument("--server", default="", help="Optional running server URL to verify (e.g. http://127.0.0.1:8093)")
    args = parser.parse_args()

    problems = 0
    print("\nDungeon Master OS — Setup & Diagnostics Check\n" + "-" * 52)

    # 1. Python version
    v = sys.version_info
    if v >= (3, 10):
        line(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        problems += 1
        line(BAD, f"Python {v.major}.{v.minor} is too old (need 3.10+)")

    # 2. Virtualenv check
    in_venv = (sys.prefix != getattr(sys, "base_prefix", sys.prefix)) or _VENV_SP.is_dir()
    line(
        OK if in_venv else WARN,
        "Virtual environment (.venv) detected" if in_venv else "Not inside .venv",
        "" if in_venv else "Run:  source .venv/bin/activate",
    )

    # 3. Required packages
    missing = []
    for mod in ("fastapi", "uvicorn", "httpx", "PIL", "pydantic", "multipart"):
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        problems += 1
        line(BAD, f"Missing packages: {', '.join(missing)}", "Run:  .venv/bin/pip install -r requirements.txt")
    else:
        line(OK, "All required packages installed (fastapi, uvicorn, httpx, pillow, pydantic, python-multipart)")

    # 4. Core modules, 6 Biomes, 4 Heroes, 3 Pre-Loaded Campaigns & D20 Math
    try:
        from dungeon_master_os import __version__
        from dungeon_master_os.battlemap import list_biomes
        from dungeon_master_os.campaigns import ensure_showcase_campaigns
        from dungeon_master_os.config import load_settings
        from dungeon_master_os.dice import SUPPORTED_DICE, dc_pass_probability, roll_polyhedral
        from dungeon_master_os.heroes import list_hero_presets

        biomes = list_biomes()
        heroes = list_hero_presets()
        camps = ensure_showcase_campaigns()
        assert len(biomes) == 6, f"Expected 6 biomes, got {len(biomes)}"
        assert len(heroes) == 4, f"Expected 4 heroes, got {len(heroes)}"
        assert len(camps) >= 3, f"Expected >=3 campaigns, got {len(camps)}"
        assert SUPPORTED_DICE == (4, 6, 8, 10, 12, 20, 100)

        p_norm = dc_pass_probability(20, 0, 11, "normal")
        p_adv = dc_pass_probability(20, 0, 11, "adv")
        assert abs(p_norm - 0.5) < 1e-6 and abs(p_adv - 0.75) < 1e-6
        r20 = roll_polyhedral(sides=20, modifier=4, dc=15, forced_natural=20)
        assert r20["is_nat20"] and r20["success"]

        line(
            OK,
            f"Dungeon Master OS v{__version__} verified ({len(biomes)} Biomes, {len(heroes)} Heroes, {len(camps)} Campaigns, d4..d100 math OK)",
        )
        s = load_settings()
        line(OK, f"4-Agent GM Engine: provider={s.effective_provider()}, model={s.effective_model()}")
    except Exception as exc:
        problems += 1
        line(BAD, f"Failed core module verification: {exc}")
        return 1

    # 5. Port 8093 status
    port = int(os.environ.get("DMOS_PORT", "8093"))
    with socket.socket() as sock:
        busy = sock.connect_ex(("127.0.0.1", port)) == 0
    line(
        OK,
        f"Port {port} is currently active / listening" if busy else f"Port {port} is free",
    )

    # 6. Optional live server check
    if args.server:
        import httpx

        try:
            r = httpx.get(f"{args.server.rstrip('/')}/api/health", timeout=5.0)
            r.raise_for_status()
            data = r.json()
            assert data.get("status") == "ok"
            line(OK, f"Live server health check at {args.server}/api/health: OK ({data.get('campaigns_count')} campaigns)")
        except Exception as exc:
            problems += 1
            line(BAD, f"Live server check failed at {args.server}: {exc}")

    print("-" * 52)
    if problems:
        print(f"{problems} issue(s) need attention.\n")
        return 1
    print("RESULT: OK — Ready to roll! Start with:  ./run.sh  or  python3 server.py\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
