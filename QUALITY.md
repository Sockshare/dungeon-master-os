# Quality Gates Report (`QUALITY.md`)

Verification record for **Dungeon Master OS (`dungeon-master-os` v1.0.0)** on port **`8093`**.

| Gate | Description | Status | Evidence / Summary |
|---|---|---|---|
| **G1** | Unit tests for core tabletop mechanics (`tests/unit/`) | **PASS** | `tests/unit/test_core_mechanics.py` — verifies all 7 polyhedral dice (`d4`, `d6`, `d8`, `d10`, `d12`, `d20`, `d100`), Advantage/Disadvantage math, exact DC pass probabilities, `Nat 20` Critical Hit & `Nat 1` Critical Fumble resolution, 4 Hero presets, inventory/potion/XP level-up logic, 6 procedural battlemap biomes, Bresenham line-of-sight Fog of War, range measurement (`5 ft/tile`), and the 4-Agent GM Engine + 5-tier NPC Disposition Meter (`Hostile` ↔ `Sworn Ally`). |
| **G2** | API smoke tests (`tests/smoke/` & `scripts/selfcheck.py`) | **PASS** | `tests/smoke/test_api_smoke.py` + `.venv/bin/python scripts/selfcheck.py --server http://127.0.0.1:8093` — verifies `/api/health`, `/api/catalog`, `/api/campaigns`, `/api/campaigns/{id}/action`, `/api/campaigns/{id}/move`, `/api/campaigns/{id}/fog`, `/api/campaigns/{id}/biome`, `/api/dice/roll`, `/api/dice/stats`, `/api/campaigns/{id}/export.md`, `/api/campaigns/{id}/export.html`, and `/api/campaigns/{id}/battlemap.png`. |
| **G3** | Standalone & Run Nexus entrypoint (`server.py`, `app.py`, `./run.sh`) | **PASS** | `server.py` and `app.py` include `_VENV_SP` auto-injection and default to port `8093` (`DMOS_PORT`). `./run.sh` provisions `.venv`, installs dependencies, and boots Uvicorn cleanly. |
| **G4** | Zero JS console/page errors across all views in headless Chromium | **PASS** | `tests/ui/test_ui_playwright.py` (Playwright `1.49.1` against Chromium `1148`) visits all 5 views (`#view-deck`, `#view-dice`, `#view-hero`, `#view-campaigns`, `#view-settings`), interacts with the Battlemap Canvas, 4-Agent GM Composer, NPC Disposition buttons, Polyhedral Dice Tray (`Nat 20` test), Hero Sheet, and Web Audio synthesizer with `console` error and `pageerror` listeners attached: **0 console errors, 0 page errors, 0 horizontal overflow at 1440px and 390px**. |
| **G5** | Real screenshots captured into `docs/screenshots/` | **PASS** | 6 full-viewport (`1440×920`) PNG screenshots captured in `docs/screenshots/` and embedded in `README.md`. |
| **G6** | 100% Offline mode + Local Ollama / Cloud LLM support | **PASS** | Verified end-to-end with `DMOS_PROVIDER=offline` (`dmos-procedural-gm-v1`) as well as configurable `ollama`, `openai`, and `anthropic` providers in `/api/settings`. |
| **G7** | Privacy & path hygiene | **PASS** | `config.display_path()` formats all UI-visible paths relative to the project root (`./data`, `./data/settings.json`), leaking zero host filesystem paths or secrets. |

---

## Screenshots Inventory (`docs/screenshots/`)

| File | View / Feature Verified | Resolution |
|---|---|---|
| `docs/screenshots/01_command_deck_battlemap.png` | Command Deck, Interactive Battlemap Canvas, Fog-of-War & Tactical Initiative | `1440×920` |
| `docs/screenshots/02_gm_chronicle_and_npc_disposition.png` | 4-Agent GM Chronicle Turn & NPC Persistent Disposition Meter (`Hostile` ↔ `Sworn Ally`) | `1440×920` |
| `docs/screenshots/03_polyhedral_dice_tray.png` | 3D/Animated Polyhedral Dice Tray (`d4`–`d100`), `Nat 20` Fanfare & Probability Histogram | `1440×920` |
| `docs/screenshots/04_hero_builder_and_spellbook.png` | Hero Builder, Ability Scores, Inventory/Potions & Arcane Spellbook | `1440×920` |
| `docs/screenshots/05_campaigns_vault_and_export.png` | 3 Pre-Loaded Playable Campaigns Vault & Markdown/HTML Chronicle Export | `1440×920` |
| `docs/screenshots/06_ai_and_audio_settings.png` | 4-Agent GM Provider Configuration & Web Audio Soundscape Synthesizer | `1440×920` |
