"""Procedural Multi-Room Battlemap Generator, Fog-of-War & Token Movement Engine."""

from __future__ import annotations

from collections import deque
import io
import math
import random
from typing import Any

from PIL import Image, ImageDraw

BIOME_CATALOG: dict[str, dict[str, Any]] = {
    "sunken_obsidian_crypt": {
        "id": "sunken_obsidian_crypt",
        "name": "Sunken Obsidian Crypt",
        "subtitle": "Subterranean necropolis of basalt vaults, soul-braziers & ancient sarcophagi",
        "ambient_key": "crypt_drone",
        "floor_color": "#1e1b2e",
        "wall_color": "#0d0b14",
        "accent_color": "#a855f7",
        "hazard_type": "arcane_rune",
        "hazard_name": "Necrotic Soul-Rune",
        "light_name": "Violet Soul-Brazier",
        "room_names": [
            "Vestibule of Weeping Basalt",
            "Ossuary of the Silent Legion",
            "Hall of Eclipse Mirrors",
            "Sanctum of the Sunken Crown",
        ],
        "loot_pool": [
            {"id": "ring_eclipse", "name": "Signet of the Eclipse King", "type": "armor", "bonus_ac": 1, "qty": 1, "desc": "Ancient obsidian ring (+1 AC)."},
            {"id": "vial_grave_elixir", "name": "Elixir of Undying Vigor", "type": "potion", "heal_amount": 18, "mana_amount": 6, "qty": 1, "desc": "Restores 18 HP and 6 Mana."},
            {"id": "blade_morrow", "name": "Morrow-Glass Longsword", "type": "weapon", "damage_dice": "2d8+4", "attack_ability": "STR", "bonus_ac": 0, "qty": 1, "desc": "Volcanic glass blade that cleaves armor."},
        ],
    },
    "dragons_ember_cavern": {
        "id": "dragons_ember_cavern",
        "name": "Dragon's Ember Cavern",
        "subtitle": "Volcanic caldera of rivers of magma, basalt bridges & draconic hoard vaults",
        "ambient_key": "ember_rumble",
        "floor_color": "#2a1612",
        "wall_color": "#140907",
        "accent_color": "#f97316",
        "hazard_type": "lava",
        "hazard_name": "Molten Magma Fissure",
        "light_name": "Pyroclast Brazier",
        "room_names": [
            "Scorched Basalt Threshold",
            "Magma-Span Causeway",
            "Cinder-Drake Hatchery",
            "Caldera Hoard Vault",
        ],
        "loot_pool": [
            {"id": "drake_scale_shield", "name": "Crimson Drake-Scale Buckler", "type": "armor", "bonus_ac": 2, "qty": 1, "desc": "Fire-hardened dragonscale shield (+2 AC)."},
            {"id": "emberheart_draught", "name": "Emberheart Phoenix Draught", "type": "potion", "heal_amount": 20, "mana_amount": 8, "qty": 1, "desc": "Restores 20 HP and 8 Mana with liquid fire."},
            {"id": "pyrebrand_halberd", "name": "Pyrebrand Greataxe", "type": "weapon", "damage_dice": "2d10+4", "attack_ability": "STR", "bonus_ac": 0, "qty": 1, "desc": "Searing draconic steel weapon."},
        ],
    },
    "clockwork_astral_spire": {
        "id": "clockwork_astral_spire",
        "name": "Clockwork Astral Spire",
        "subtitle": "Celestial observatory of interlocking brass gears, chrono-runes & starlight conduits",
        "ambient_key": "clockwork_hum",
        "floor_color": "#152232",
        "wall_color": "#0a111a",
        "accent_color": "#38bdf8",
        "hazard_type": "arcane_rune",
        "hazard_name": "Temporal Flux Glyph",
        "light_name": "Aether Pendulum Beacon",
        "room_names": [
            "Orrery Landing Deck",
            "Gallery of Whirring Escapements",
            "Chrono-Capacitor Rotunda",
            "Apex Starlight Vault",
        ],
        "loot_pool": [
            {"id": "chrono_lens", "name": "Astrolabe Monocle of Foresight", "type": "armor", "bonus_ac": 1, "qty": 1, "desc": "Predicts incoming trajectories (+1 AC)."},
            {"id": "aether_cell", "name": "Condensed Starlight Flask", "type": "potion", "heal_amount": 15, "mana_amount": 12, "qty": 1, "desc": "Restores 15 HP and 12 Mana."},
            {"id": "celestial_lance", "name": "Starforged Chrono-Sabre", "type": "weapon", "damage_dice": "2d8+5", "attack_ability": "INT", "bonus_ac": 0, "qty": 1, "desc": "Resonates with arcane intellect."},
        ],
    },
    "whispering_feywild_grove": {
        "id": "whispering_feywild_grove",
        "name": "Whispering Feywild Grove",
        "subtitle": "Twilight sylvan sanctuary of bioluminescent spores, rime-ice glades & fairy rings",
        "ambient_key": "fey_wind",
        "floor_color": "#132820",
        "wall_color": "#08140f",
        "accent_color": "#34d399",
        "hazard_type": "ice",
        "hazard_name": "Winter-Court Rime Slick",
        "light_name": "Moon-Spore Lantern",
        "room_names": [
            "Hollow of Silver Willows",
            "Glimmer-Moss Crossing",
            "Ring of the Gloaming Toadstools",
            "Heartwood Shrine of Queen Mab",
        ],
        "loot_pool": [
            {"id": "sylvan_cloak", "name": "Cloak of Shifting Leaves", "type": "armor", "bonus_ac": 2, "qty": 1, "desc": "Feywild mantle that blurs outline (+2 AC)."},
            {"id": "moonberry_nectar", "name": "Moonberry Dew Nectar", "type": "potion", "heal_amount": 18, "mana_amount": 10, "qty": 1, "desc": "Restores 18 HP and 10 Mana."},
            {"id": "thornbow", "name": "Briar-Song Shortbow", "type": "weapon", "damage_dice": "2d8+4", "attack_ability": "DEX", "bonus_ac": 0, "qty": 1, "desc": "Living yew bow strung with silver gossamer."},
        ],
    },
    "rustport_tavern_brawl": {
        "id": "rustport_tavern_brawl",
        "name": "Rustport Tavern Brawl",
        "subtitle": "Rowdy dockside taproom of overturned oak tables, chandelier swings & smuggler vaults",
        "ambient_key": "tavern_hearth",
        "floor_color": "#2b1f14",
        "wall_color": "#140e08",
        "accent_color": "#eab308",
        "hazard_type": "ice",
        "hazard_name": "Spilled Dwarven Ale Slick",
        "light_name": "Wrought-Iron Chandelier",
        "room_names": [
            "The Salty Kraken Taproom",
            "Brawler's Mezzanine & Hearth",
            "Smuggler's Rum Cellar",
            "Harbormaster's Hidden Strongroom",
        ],
        "loot_pool": [
            {"id": "corsair_coat", "name": "Steel-Lined Corsair Greatcoat", "type": "armor", "bonus_ac": 2, "qty": 1, "desc": "Turns away tavern knives (+2 AC)."},
            {"id": "kraken_stout", "name": "Vintage Kraken-Spiced Rum", "type": "potion", "heal_amount": 16, "mana_amount": 6, "qty": 1, "desc": "Restores 16 HP and 6 Mana."},
            {"id": "cutlass_storm", "name": "Storm-Caller Boarding Cutlass", "type": "weapon", "damage_dice": "2d8+4", "attack_ability": "DEX", "bonus_ac": 0, "qty": 1, "desc": "Crackles with dockside lightning."},
        ],
    },
    "starship_derelict_deck": {
        "id": "starship_derelict_deck",
        "name": "Starship Derelict Deck",
        "subtitle": "Zero-G astral dreadnought deck with cryo-leaks, plasma conduits & airlock bulkheads",
        "ambient_key": "starship_pulse",
        "floor_color": "#141d2b",
        "wall_color": "#090d14",
        "accent_color": "#22d3ee",
        "hazard_type": "lava",
        "hazard_name": "Ruptured Plasma Conduit",
        "light_name": "Emergency Holo-Strobe",
        "room_names": [
            "Docking Airlock Bay 04",
            "Cryo-Stasis Corridor",
            "Reactor Aux-Control Deck",
            "Command Bridge Core",
        ],
        "loot_pool": [
            {"id": "void_weave_vest", "name": "Exo-Mesh Deflector Vest", "type": "armor", "bonus_ac": 2, "qty": 1, "desc": "Absorbs kinetic and plasma impacts (+2 AC)."},
            {"id": "nanomed_injector", "name": "Mk-V Nano-Med Injector", "type": "potion", "heal_amount": 20, "mana_amount": 8, "qty": 1, "desc": "Restores 20 HP and 8 Mana."},
            {"id": "photon_blade", "name": "Phase-Edge Vibroblade", "type": "weapon", "damage_dice": "2d8+5", "attack_ability": "DEX", "bonus_ac": 0, "qty": 1, "desc": "High-frequency molecular blade."},
        ],
    },
}


def list_biomes() -> list[dict[str, Any]]:
    return [
        {
            "id": b["id"],
            "name": b["name"],
            "subtitle": b["subtitle"],
            "ambient_key": b["ambient_key"],
            "floor_color": b["floor_color"],
            "wall_color": b["wall_color"],
            "accent_color": b["accent_color"],
            "hazard_type": b["hazard_type"],
            "hazard_name": b["hazard_name"],
            "room_names": b["room_names"],
        }
        for b in BIOME_CATALOG.values()
    ]


def tile_distance_ft(x1: int, y1: int, x2: int, y2: int) -> int:
    """Measure tabletop distance in feet where 1 grid tile = 5 ft."""
    return int(round(math.hypot(x2 - x1, y2 - y1) * 5))


def generate_battlemap(biome_id: str = "sunken_obsidian_crypt", seed: int | None = None) -> dict[str, Any]:
    """Generate a connected 16x12 multi-room procedural battlemap with doors, traps, chests, hazards & lighting."""
    biome = BIOME_CATALOG.get(biome_id) or BIOME_CATALOG["sunken_obsidian_crypt"]
    rng = random.Random(seed if seed is not None else hash(biome_id) & 0xFFFFFFFF)

    width, height = 16, 12
    # Initialize all walls
    tiles: list[list[dict[str, Any]]] = [
        [
            {
                "x": x,
                "y": y,
                "kind": "wall",
                "room_id": None,
                "hazard": None,
                "light": False,
                "chest": None,
                "trap": None,
                "opened": False,
            }
            for x in range(width)
        ]
        for y in range(height)
    ]

    # 4 well-proportioned rooms across the 16x12 grid
    room_rects = [
        {"id": "room_1", "name": biome["room_names"][0], "x1": 1, "y1": 1, "x2": 6, "y2": 5},
        {"id": "room_2", "name": biome["room_names"][1], "x1": 9, "y1": 1, "x2": 14, "y2": 5},
        {"id": "room_3", "name": biome["room_names"][2], "x1": 1, "y1": 7, "x2": 6, "y2": 10},
        {"id": "room_4", "name": biome["room_names"][3], "x1": 9, "y1": 7, "x2": 14, "y2": 10},
    ]

    for rm in room_rects:
        for y in range(rm["y1"], rm["y2"] + 1):
            for x in range(rm["x1"], rm["x2"] + 1):
                tiles[y][x]["kind"] = "floor"
                tiles[y][x]["room_id"] = rm["id"]

    # Carve interconnecting corridors with doors
    # Horizontal corridor top: (7, 3) and (8, 3)
    for x in (7, 8):
        tiles[3][x]["kind"] = "door" if x == 7 else "floor"
        tiles[3][x]["room_id"] = "corridor_top"
    # Horizontal corridor bottom: (7, 8) and (8, 8)
    for x in (7, 8):
        tiles[8][x]["kind"] = "door" if x == 8 else "floor"
        tiles[8][x]["room_id"] = "corridor_bottom"
    # Vertical corridor left: (3, 6)
    tiles[6][3]["kind"] = "door"
    tiles[6][3]["room_id"] = "corridor_left"
    # Vertical corridor right: (11, 6)
    tiles[6][11]["kind"] = "door"
    tiles[6][11]["room_id"] = "corridor_right"

    # Place atmospheric pillars inside rooms
    for px, py in ((4, 2), (12, 2), (4, 9), (12, 9)):
        tiles[py][px]["kind"] = "pillar"

    # Place light sources (braziers/lanterns)
    lights = [
        {"x": 2, "y": 2, "radius": 4, "name": biome["light_name"]},
        {"x": 10, "y": 2, "radius": 4, "name": biome["light_name"]},
        {"x": 2, "y": 8, "radius": 4, "name": biome["light_name"]},
        {"x": 13, "y": 8, "radius": 4, "name": biome["light_name"]},
    ]
    for lt in lights:
        tiles[lt["y"]][lt["x"]]["light"] = True

    # Place environmental hazards (lava fissures & arcane runes)
    hazard_coords = [
        (10, 4, "lava"),
        (11, 4, "lava"),
        (3, 8, "arcane_rune"),
        (11, 8, biome["hazard_type"]),
    ]
    for hx, hy, hkind in hazard_coords:
        if tiles[hy][hx]["kind"] == "floor":
            tiles[hy][hx]["hazard"] = {
                "type": hkind,
                "name": "Molten Magma Fissure" if hkind == "lava" else (biome["hazard_name"] if hkind == biome["hazard_type"] else "Arcane Ley-Rune"),
                "damage": 4 if hkind == "lava" else (2 if hkind == "ice" else 0),
                "buff_mana": 3 if hkind == "arcane_rune" else 0,
            }

    # Place 3 Treasure Chests with biome loot
    loot_items = biome["loot_pool"]
    chest_positions = [(5, 1, 0), (13, 1, 1), (13, 10, 2)]
    for cx, cy, lidx in chest_positions:
        item = loot_items[lidx % len(loot_items)]
        tiles[cy][cx]["chest"] = {
            "id": f"chest_{cx}_{cy}",
            "name": f"Ornate {biome['name'].split()[0]} Chest",
            "opened": False,
            "gold": 45 + lidx * 25,
            "item": item,
        }

    # Place 3 Hidden/Armed Traps
    trap_positions = [
        {"x": 6, "y": 3, "name": "Pressure-Plate Dart Trap", "dc": 13, "ability": "DEX", "damage": 6},
        {"x": 10, "y": 3, "name": "Glyph of Warding Snare", "dc": 14, "ability": "WIS", "damage": 7},
        {"x": 8, "y": 8, "name": "Scything Pendulum Trigger", "dc": 15, "ability": "DEX", "damage": 8},
    ]
    for tr in trap_positions:
        tiles[tr["y"]][tr["x"]]["trap"] = {
            "id": f"trap_{tr['x']}_{tr['y']}",
            "name": tr["name"],
            "dc": tr["dc"],
            "ability": tr["ability"],
            "damage": tr["damage"],
            "triggered": False,
            "disarmed": False,
        }

    # Place sanctum exit portal at (14, 10)
    tiles[10][14]["kind"] = "exit"

    hero_pos = {"x": 2, "y": 3}
    bmap: dict[str, Any] = {
        "biome_id": biome["id"],
        "biome_name": biome["name"],
        "biome_subtitle": biome["subtitle"],
        "ambient_key": biome["ambient_key"],
        "floor_color": biome["floor_color"],
        "wall_color": biome["wall_color"],
        "accent_color": biome["accent_color"],
        "width": width,
        "height": height,
        "tile_scale_ft": 5,
        "rooms": room_rects,
        "lights": lights,
        "hero_pos": hero_pos,
        "fog_of_war": True,
        "revealed": [],
        "visible": [],
        "tiles": tiles,
    }
    update_fog_of_war(bmap, vision_radius=5)
    return bmap


def _has_line_of_sight(tiles: list[list[dict[str, Any]]], x0: int, y0: int, x1: int, y1: int) -> bool:
    """Bresenham raycast to check if walls or closed doors block line of sight."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1

    if dx > dy:
        err = dx / 2.0
        while x != x1:
            if (x, y) != (x0, y0) and (x, y) != (x1, y1):
                cell = tiles[y][x]
                if cell["kind"] in ("wall", "pillar") or (cell["kind"] == "door" and not cell.get("opened")):
                    return False
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != y1:
            if (x, y) != (x0, y0) and (x, y) != (x1, y1):
                cell = tiles[y][x]
                if cell["kind"] in ("wall", "pillar") or (cell["kind"] == "door" and not cell.get("opened")):
                    return False
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
    return True


def update_fog_of_war(bmap: dict[str, Any], vision_radius: int = 5) -> dict[str, Any]:
    """Update visible and permanently revealed coordinates around hero_pos."""
    hx = int(bmap["hero_pos"]["x"])
    hy = int(bmap["hero_pos"]["y"])
    width = int(bmap["width"])
    height = int(bmap["height"])
    tiles = bmap["tiles"]

    revealed_set = {tuple(p) for p in bmap.get("revealed", [])}
    visible_now: set[tuple[int, int]] = set()

    for y in range(height):
        for x in range(width):
            dist = math.hypot(x - hx, y - hy)
            if dist <= vision_radius + 0.35:
                if _has_line_of_sight(tiles, hx, hy, x, y):
                    visible_now.add((x, y))
                    revealed_set.add((x, y))

    bmap["visible"] = [list(p) for p in sorted(visible_now)]
    bmap["revealed"] = [list(p) for p in sorted(revealed_set)]
    return bmap


def shortest_walkable_path(
    bmap: dict[str, Any],
    start: tuple[int, int],
    goal: tuple[int, int],
    max_steps: int = 8,
) -> list[tuple[int, int]]:
    """Find shortest walkable path on grid (doors are walkable and auto-open)."""
    width, height = int(bmap["width"]), int(bmap["height"])
    tiles = bmap["tiles"]
    gx, gy = goal
    if not (0 <= gx < width and 0 <= gy < height):
        return []
    if tiles[gy][gx]["kind"] in ("wall", "pillar"):
        return []

    q: deque[tuple[tuple[int, int], list[tuple[int, int]]]] = deque([(start, [])])
    visited = {start}
    while q:
        (cx, cy), path = q.popleft()
        if (cx, cy) == goal:
            return path[:max_steps]
        if len(path) >= max_steps:
            continue
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1), (cx + 1, cy + 1), (cx - 1, cy - 1), (cx + 1, cy - 1), (cx - 1, cy + 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                cell = tiles[ny][nx]
                if cell["kind"] not in ("wall", "pillar"):
                    visited.add((nx, ny))
                    q.append(((nx, ny), path + [(nx, ny)]))
    return []


def current_room_name(bmap: dict[str, Any]) -> str:
    hx, hy = int(bmap["hero_pos"]["x"]), int(bmap["hero_pos"]["y"])
    cell = bmap["tiles"][hy][hx]
    rid = cell.get("room_id")
    for rm in bmap.get("rooms", []):
        if rm["id"] == rid:
            return rm["name"]
    return "Connecting Vault Corridor"


def render_battlemap_png(campaign: dict[str, Any]) -> bytes:
    """Render a crisp high-resolution tabletop battlemap PNG using Pillow."""
    bmap = campaign["battlemap"]
    width, height = int(bmap["width"]), int(bmap["height"])
    cell_px = 48
    img_w = width * cell_px
    img_h = height * cell_px + 56

    img = Image.new("RGB", (img_w, img_h), "#0b0d14")
    draw = ImageDraw.Draw(img)

    revealed = {tuple(p) for p in bmap.get("revealed", [])}
    visible = {tuple(p) for p in bmap.get("visible", [])}
    fog_enabled = bool(bmap.get("fog_of_war", True))

    floor_rgb = bmap.get("floor_color", "#1e1b2e")
    wall_rgb = bmap.get("wall_color", "#0d0b14")
    accent_rgb = bmap.get("accent_color", "#a855f7")

    for y in range(height):
        for x in range(width):
            x0, y0 = x * cell_px, y * cell_px + 56
            x1, y1 = x0 + cell_px, y0 + cell_px
            cell = bmap["tiles"][y][x]
            is_rev = (not fog_enabled) or ((x, y) in revealed)
            is_vis = (not fog_enabled) or ((x, y) in visible)

            if not is_rev:
                draw.rectangle([x0, y0, x1, y1], fill="#07080d", outline="#11131f")
                continue

            kind = cell["kind"]
            fill = wall_rgb if kind in ("wall", "pillar") else floor_rgb
            if kind == "door":
                fill = "#78350f" if not cell.get("opened") else "#3f2e21"
            elif kind == "exit":
                fill = "#1d4ed8"

            draw.rectangle([x0, y0, x1, y1], fill=fill, outline="#2a2f45")

            if cell.get("hazard"):
                htype = cell["hazard"]["type"]
                hcol = "#ea580c" if htype == "lava" else ("#38bdf8" if htype == "ice" else "#a855f7")
                draw.ellipse([x0 + 8, y0 + 8, x1 - 8, y1 - 8], outline=hcol, width=2)

            if cell.get("chest") and not cell["chest"].get("opened"):
                draw.rectangle([x0 + 12, y0 + 14, x1 - 12, y1 - 12], fill="#eab308", outline="#fef08a")

            if cell.get("trap") and cell["trap"].get("triggered"):
                draw.line([x0 + 10, y0 + 10, x1 - 10, y1 - 10], fill="#ef4444", width=2)
                draw.line([x0 + 10, y1 - 10, x1 - 10, y0 + 10], fill="#ef4444", width=2)

            if not is_vis:
                # Dim explored-but-out-of-sight tiles
                draw.rectangle([x0, y0, x1, y1], outline="#151824")

    # Draw NPCs
    for npc in campaign.get("npcs", []):
        nx, ny = int(npc.get("x", 3)), int(npc.get("y", 2))
        if (not fog_enabled) or ((nx, ny) in revealed):
            cx, cy = nx * cell_px + cell_px // 2, ny * cell_px + 56 + cell_px // 2
            draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill="#10b981", outline="#ecfdf5", width=2)

    # Draw living monsters
    for mon in campaign.get("monsters", []):
        if int(mon.get("hp", 0)) <= 0:
            continue
        mx, my = int(mon.get("x", 10)), int(mon.get("y", 3))
        if (not fog_enabled) or ((mx, my) in revealed):
            cx, cy = mx * cell_px + cell_px // 2, my * cell_px + 56 + cell_px // 2
            draw.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill="#ef4444", outline="#fee2e2", width=2)

    # Draw Hero Token
    hx, hy = int(bmap["hero_pos"]["x"]), int(bmap["hero_pos"]["y"])
    hcx, hcy = hx * cell_px + cell_px // 2, hy * cell_px + 56 + cell_px // 2
    draw.ellipse([hcx - 17, hcy - 17, hcx + 17, hcy + 17], fill=accent_rgb, outline="#ffffff", width=3)

    # Header banner
    draw.rectangle([0, 0, img_w, 55], fill="#111522")
    title = f"DUNGEON MASTER OS  |  {bmap['biome_name']}  |  Hero @ ({hx}, {hy}) [Scale: 5 ft/tile]"
    draw.text((16, 18), title, fill="#f8fafc")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
