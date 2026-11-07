"""FastAPI application and REST API endpoints for Dungeon Master OS."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from dungeon_master_os import __version__
from dungeon_master_os.agents import (
    TacticalDirectorAgent,
    WorldbuilderGMAgent,
    move_hero_token,
    run_gm_turn,
)
from dungeon_master_os.battlemap import (
    BIOME_CATALOG,
    generate_battlemap,
    list_biomes,
    render_battlemap_png,
    update_fog_of_war,
)
from dungeon_master_os.campaigns import (
     _creatures_for_biome,
    create_campaign,
    ensure_showcase_campaigns,
    export_chronicle_html,
    export_chronicle_markdown,
    list_campaigns,
    load_campaign,
    reset_showcase_campaign,
    save_campaign,
)
from dungeon_master_os.config import DMOSSettings, load_settings, save_settings
from dungeon_master_os.dice import DiceMode, SUPPORTED_DICE, distribution_stats, roll_polyhedral
from dungeon_master_os.heroes import (
    award_xp,
    build_hero,
    equip_Or_use_item,
    list_hero_presets,
    recalc_hero,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    ensure_showcase_campaigns()
    yield


app = FastAPI(
    title="Dungeon Master OS",
    description="Autonomous Solo & Party Tabletop RPG Command Deck & Procedural Battlemap Studio",
    version=__version__,
    lifespan=_lifespan,
)


@app.middleware("http")
async def _no_store_cache_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


class CreateCampaignRequest(BaseModel):
    title: str = Field(default="Shadows of the Obsidian Vault")
    biome_id: str = Field(default="sunken_obsidian_crypt")
    hero_preset_id: str = Field(default="kaelen_paladin")
    synopsis: str = Field(default="")
    hero_overrides: dict[str, Any] | None = None


class ActionRequest(BaseModel):
    action_text: str = Field(..., min_length=1)
    action_type: str = Field(default="roleplay")
    dice_mode: DiceMode = Field(default="normal")
    player_d20_roll: int | None = None
    target_npc_id: str | None = None
    target_monster_id: str | None = None


class MoveRequest(BaseModel):
    x: int
    y: int


class FogRequest(BaseModel):
    fog_of_war: bool | None = None
    reveal_all: bool = False


class BiomeSwitchRequest(BaseModel):
    biome_id: str
    seed: int | None = None


class DiceRollRequest(BaseModel):
    sides: int = Field(default=20)
    count: int = Field(default=1)
    modifier: int = Field(default=0)
    mode: DiceMode = Field(default="normal")
    dc: int | None = None
    label: str = Field(default="")
    campaign_id: str | None = None
    forced_natural: int | None = None


class HeroItemRequest(BaseModel):
    item_id: str


class HeroProgressRequest(BaseModel):
    action: str = Field(default="rest")  # "rest" | "xp"
    xp_amount: int = Field(default=500)


class HeroCustomizeRequest(BaseModel):
    preset_id: str | None = None
    name: str | None = None
    class_name: str | None = None
    ancestry: str | None = None
    abilities: dict[str, int] | None = None


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    campaigns = ensure_showcase_campaigns()
    settings = load_settings()
    return {
        "status": "ok",
        "app": "dungeon-master-os",
        "version": __version__,
        "provider": settings.effective_provider(),
        "model": settings.effective_model(),
        "campaigns_count": len(campaigns),
        "biomes_count": len(BIOME_CATALOG),
        "heroes_count": len(list_hero_presets()),
    }


@app.get("/api/catalog")
def api_catalog() -> dict[str, Any]:
    settings = load_settings()
    return {
        "biomes": list_biomes(),
        "heroes": list_hero_presets(),
        "supported_dice": list(SUPPORTED_DICE),
        "settings": settings.public_dict(),
    }


@app.get("/api/campaigns")
def api_list_campaigns() -> dict[str, Any]:
    items = ensure_showcase_campaigns()
    return {"campaigns": items}


@app.post("/api/campaigns")
def api_create_campaign(req: CreateCampaignRequest) -> dict[str, Any]:
    camp = create_campaign(
        title=req.title.strip() or "Untitled Delve",
        biome_id=req.biome_id,
        hero_preset_id=req.hero_preset_id,
        synopsis=req.synopsis,
        hero_overrides=req.hero_overrides,
    )
    save_campaign(camp)
    return {"campaign": camp}


@app.get("/api/campaigns/{campaign_id}")
def api_get_campaign(campaign_id: str) -> dict[str, Any]:
    ensure_showcase_campaigns()
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    return {"campaign": camp}


@app.post("/api/campaigns/{campaign_id}/reset")
def api_reset_campaign(campaign_id: str) -> dict[str, Any]:
    try:
        camp = reset_showcase_campaign(campaign_id)
        return {"campaign": camp}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/campaigns/{campaign_id}/action")
def api_campaign_action(campaign_id: str, req: ActionRequest) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    turn_entry = run_gm_turn(
        campaign=camp,
        action_text=req.action_text,
        action_type=req.action_type,
        dice_mode=req.dice_mode,
        player_d20_roll=req.player_d20_roll,
        target_npc_id=req.target_npc_id,
        target_monster_id=req.target_monster_id,
    )
    save_campaign(camp)
    return {"turn": turn_entry, "campaign": camp}


@app.post("/api/campaigns/{campaign_id}/move")
def api_campaign_move(campaign_id: str, req: MoveRequest) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    try:
        move_res = move_hero_token(camp, req.x, req.y)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_campaign(camp)
    return {"move": move_res, "campaign": camp}


@app.post("/api/campaigns/{campaign_id}/fog")
def api_campaign_fog(campaign_id: str, req: FogRequest) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    bmap = camp["battlemap"]
    if req.fog_of_war is not None:
        bmap["fog_of_war"] = bool(req.fog_of_war)
    if req.reveal_all:
        w, h = int(bmap["width"]), int(bmap["height"])
        all_coords = [[x, y] for y in range(h) for x in range(w)]
        bmap["revealed"] = all_coords
        bmap["visible"] = all_coords
    else:
        update_fog_of_war(bmap, vision_radius=int(camp["hero"].get("vision_radius", 5)))
    save_campaign(camp)
    return {"campaign": camp}


@app.post("/api/campaigns/{campaign_id}/biome")
def api_campaign_switch_biome(campaign_id: str, req: BiomeSwitchRequest) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    if req.biome_id not in BIOME_CATALOG:
        raise HTTPException(status_code=400, detail=f"Unknown biome '{req.biome_id}'.")
    bmap = generate_battlemap(biome_id=req.biome_id, seed=req.seed)
    npcs, monsters = _creatures_for_biome(req.biome_id)
    camp["battlemap"] = bmap
    camp["npcs"] = npcs
    camp["monsters"] = monsters
    TacticalDirectorAgent.sync_initiative(camp)
    camp["suggested_actions"] = WorldbuilderGMAgent.suggest_actions(camp)
    camp.setdefault("chronicle", []).append(
        {
            "id": f"biome_{req.biome_id}",
            "timestamp": "Scene Shift",
            "player_action": f"Traverse realm gate into {bmap['biome_name']}",
            "action_type": "explore",
            "room_name": bmap["rooms"][0]["name"],
            "narrative": f"🌌 **REALM TRANSITION — {bmap['biome_name'].upper()}**\n\n{bmap['biome_subtitle']}. **{camp['hero']['name']}** emerges into **{bmap['rooms'][0]['name']}**.",
            "agents": {
                "worldbuilder": {"name": "Worldbuilder & Narrative GM", "summary": f"Generated {bmap['biome_name']} battlemap.", "provider": "offline"},
                "rules_lawyer": {"name": "Rules Lawyer & D20 Mechanics", "verdict": "REALM SHIFT", "summary": "Grid scale calibrated to 5 ft/tile."},
                "npc_actor": {"name": "NPC Actor & Relationship Memory", "summary": f"Spawned {len(npcs)} regional NPCs."},
                "tactical_director": {"name": "Tactical Encounter Director", "summary": f"Initialized {len(monsters)} regional monsters."},
            },
        }
    )
    save_campaign(camp)
    return {"campaign": camp}


@app.post("/api/campaigns/{campaign_id}/hero/item")
def api_hero_item(campaign_id: str, req: HeroItemRequest) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    _, msg = equip_Or_use_item(camp["hero"], req.item_id)
    TacticalDirectorAgent.sync_initiative(camp)
    save_campaign(camp)
    return {"message": msg, "campaign": camp}


@app.post("/api/campaigns/{campaign_id}/hero/progress")
def api_hero_progress(campaign_id: str, req: HeroProgressRequest) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    hero = camp["hero"]
    if req.action == "xp":
        _, leveled, msg = award_xp(hero, req.xp_amount)
    else:
        hero["hp"] = hero["max_hp"]
        hero["mana"] = hero["max_mana"]
        recalc_hero(hero)
        leveled = False
        msg = f"{hero['name']} took a Sanctum Rest: HP ({hero['hp']}/{hero['max_hp']}) and Mana ({hero['mana']}/{hero['max_mana']}) fully restored!"
    TacticalDirectorAgent.sync_initiative(camp)
    save_campaign(camp)
    return {"message": msg, "leveled_up": leveled, "campaign": camp}


@app.post("/api/campaigns/{campaign_id}/hero/customize")
def api_hero_customize(campaign_id: str, req: HeroCustomizeRequest) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    if req.preset_id:
        camp["hero"] = build_hero(
            req.preset_id,
            overrides={
                "name": req.name,
                "class_name": req.class_name,
                "ancestry": req.ancestry,
                "abilities": req.abilities,
            },
        )
    else:
        hero = camp["hero"]
        if req.name:
            hero["name"] = req.name
        if req.class_name:
            hero["class_name"] = req.class_name
        if req.ancestry:
            hero["ancestry"] = req.ancestry
        if req.abilities:
            for k, v in req.abilities.items():
                if k in hero["abilities"]:
                    hero["abilities"][k] = max(6, min(20, int(v)))
        recalc_hero(hero)
    TacticalDirectorAgent.sync_initiative(camp)
    save_campaign(camp)
    return {"campaign": camp}


@app.post("/api/dice/roll")
def api_roll_dice(req: DiceRollRequest) -> dict[str, Any]:
    res = roll_polyhedral(
        sides=req.sides,
        count=req.count,
        modifier=req.modifier,
        mode=req.mode,
        dc=req.dc,
        label=req.label,
        forced_natural=req.forced_natural,
    )
    if req.campaign_id:
        camp = load_campaign(req.campaign_id)
        if camp:
            camp.setdefault("dice_history", []).insert(0, res)
            del camp["dice_history"][40:]
            save_campaign(camp)
    return {"roll": res}


@app.get("/api/dice/stats")
def api_dice_stats(sides: int = 20, count: int = 1, modifier: int = 0, mode: DiceMode = "normal", dc: int | None = 13) -> dict[str, Any]:
    return {"stats": distribution_stats(sides=sides, count=count, modifier=modifier, mode=mode, dc=dc)}


@app.get("/api/campaigns/{campaign_id}/export.md", response_class=PlainTextResponse)
def api_export_md(campaign_id: str) -> PlainTextResponse:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    md = export_chronicle_markdown(camp)
    return PlainTextResponse(
        content=md,
        headers={"Content-Disposition": f'attachment; filename="{campaign_id}_chronicle.md"'},
    )


@app.get("/api/campaigns/{campaign_id}/export.html", response_class=HTMLResponse)
def api_export_html(campaign_id: str) -> HTMLResponse:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    html_doc = export_chronicle_html(camp)
    return HTMLResponse(
        content=html_doc,
        headers={"Content-Disposition": f'attachment; filename="{campaign_id}_chronicle.html"'},
    )


@app.get("/api/campaigns/{campaign_id}/battlemap.png")
def api_battlemap_png(campaign_id: str) -> Response:
    camp = load_campaign(campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    png_bytes = render_battlemap_png(camp)
    return Response(content=png_bytes, media_type="image/png")


@app.get("/api/settings")
def api_get_settings() -> dict[str, Any]:
    return {"settings": load_settings().public_dict()}


@app.post("/api/settings")
def api_update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = load_settings().model_dump()
    for k, v in payload.items():
        if k in current and v is not None:
            current[k] = v
    updated = save_settings(DMOSSettings(**current))
    return {"settings": updated.public_dict()}


@app.get("/", response_class=HTMLResponse)
def index_page() -> HTMLResponse:
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
