"""Playwright headless Chromium UI verification & screenshot capture for Dungeon Master OS."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
SCREENSHOT_DIR = ROOT / "docs" / "screenshots"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("dmos_ui_data")
    port = _free_port()
    env = os.environ.copy()
    env["DMOS_DATA_DIR"] = str(data_dir)
    env["DMOS_PROVIDER"] = "offline"
    env["DMOS_PORT"] = str(port)

    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py"), "--port", str(port), "--host", "127.0.0.1"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            r = httpx.get(f"{base_url}/api/health", timeout=1.5)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.25)
    else:
        proc.kill()
        out = proc.stdout.read().decode("utf-8", errors="ignore") if proc.stdout else ""
        raise RuntimeError(f"Dungeon Master OS test server did not start in time:\n{out}")

    yield base_url
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_ui_all_views_zero_errors_and_screenshots(live_server: str) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []

    # Verify Cache-Control: no-store header is present on responses
    resp = httpx.get(live_server, timeout=5.0)
    assert "no-store" in resp.headers.get("Cache-Control", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Verify High-DPI (device_scale_factor=2) renders the 16x12 board with zero resize loop
        hidpi_ctx = browser.new_context(viewport={"width": 1440, "height": 960}, device_scale_factor=2)
        hidpi_page = hidpi_ctx.new_page()
        hidpi_page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        hidpi_page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        hidpi_page.goto(live_server, wait_until="networkidle")
        hidpi_page.wait_for_selector("#battlemapCanvas")
        hidpi_page.wait_for_timeout(400)

        board_metrics = hidpi_page.evaluate(
            """() => {
                const c = document.getElementById('battlemapCanvas');
                const b3d = window.Battlemap3D;
                return {
                    dpr: window.devicePixelRatio,
                    clientW: c.clientWidth,
                    clientH: c.clientHeight,
                    canvasW: c.width,
                    canvasH: c.height,
                    rows: b3d && b3d.tileMeshes ? b3d.tileMeshes.length : 0,
                    cols: b3d && b3d.tileMeshes && b3d.tileMeshes[0] ? b3d.tileMeshes[0].length : 0,
                };
            }"""
        )
        assert board_metrics["dpr"] == 2
        assert board_metrics["clientW"] >= 600
        assert board_metrics["clientH"] >= 520
        assert board_metrics["canvasW"] == board_metrics["clientW"] * 2
        assert board_metrics["canvasH"] == board_metrics["clientH"] * 2
        hidpi_ctx.close()

        context = browser.new_context(viewport={"width": 1440, "height": 960}, device_scale_factor=1)
        page = context.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        # 1. Load Command Deck & Battlemap View
        page.goto(live_server, wait_until="networkidle")
        page.wait_for_selector("#battlemapCanvas")
        page.wait_for_selector("#npcCardsContainer .npc-card")
        assert page.locator("#initiativeOrderList .init-card").count() >= 3

        # Move Hero token on the 3D Battlemap using D-pad & trigger 3D Fireball VFX
        page.click("#moveEastBtn")
        page.wait_for_timeout(250)
        page.click("#moveNorthBtn")
        page.wait_for_timeout(250)
        page.click("#vfxFireballBtn")
        page.wait_for_timeout(480)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(80)
        page.screenshot(path=str(SCREENSHOT_DIR / "01_command_deck_battlemap.png"), full_page=False)

        # 2. Trigger 4-Agent GM Turn & NPC Disposition Shift + Chain Lightning VFX
        page.locator("#npcCardsContainer .npc-act-btn").first.click()
        page.wait_for_timeout(400)
        page.click("#vfxLightningBtn")
        page.wait_for_timeout(260)
        assert page.locator("#chronicleFeed .chronicle-entry").count() >= 2
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(80)
        page.screenshot(path=str(SCREENSHOT_DIR / "02_gm_chronicle_and_npc_disposition.png"), full_page=False)

        # 3. Switch to 3D Polyhedral Dice Tray & Odds Studio
        page.click("#navDiceBtn")
        page.wait_for_selector("#view-dice.active")
        page.click("#forceNat20Btn")
        page.wait_for_timeout(420)
        assert "NATURAL 20" in page.locator("#diceResultHeadline").inner_text().upper()
        page.screenshot(path=str(SCREENSHOT_DIR / "03_polyhedral_dice_tray.png"), full_page=False)

        # 4. Switch to Hero Builder, Inventory & Spellbook View
        page.click("#navHeroBtn")
        page.wait_for_selector("#view-hero.active")
        assert page.locator("#heroPresetsStrip .preset-hero-card").count() == 4
        page.click("#heroGrantXpBtn")
        page.wait_for_timeout(300)
        page.screenshot(path=str(SCREENSHOT_DIR / "04_hero_builder_and_spellbook.png"), full_page=False)

        # 5. Switch to Campaigns Vault & Chronicle Export View
        page.click("#navCampaignsBtn")
        page.wait_for_selector("#view-campaigns.active")
        assert page.locator("#campaignsVaultGrid .vault-camp-card").count() >= 3
        page.wait_for_timeout(300)
        page.screenshot(path=str(SCREENSHOT_DIR / "05_campaigns_vault_and_export.png"), full_page=False)

        # 6. Switch to AI & Audio Settings View
        page.click("#navSettingsBtn")
        page.wait_for_selector("#view-settings.active")
        page.click("#testCritSoundBtn")
        page.wait_for_timeout(250)
        page.screenshot(path=str(SCREENSHOT_DIR / "06_ai_and_audio_settings.png"), full_page=False)

        # Return to 3D Deck and verify zero horizontal overflow on both desktop (1440px) and mobile (375x812)
        page.click("#navDeckBtn")
        for vw, vh in ((1440, 960), (375, 812)):
            page.set_viewport_size({"width": vw, "height": vh})
            page.wait_for_timeout(200)
            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2"
            )
            assert not overflow, f"Horizontal overflow detected at viewport width {vw}px"
            if vw == 375:
                page.screenshot(path=str(SCREENSHOT_DIR / "07_mobile_3d_deck.png"), full_page=False)

        browser.close()

    assert console_errors == [], f"Browser console errors detected: {console_errors}"
    assert page_errors == [], f"Browser page errors detected: {page_errors}"
