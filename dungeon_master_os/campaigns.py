"""Pre-loaded playable campaigns, Campaign Builder, Save/Load & Chronicle Export (Markdown & HTML)."""

from __future__ import annotations

import html
import json
import time
from typing import Any

from dungeon_master_os.agents import (
    TacticalDirectorAgent,
    WorldbuilderGMAgent,
    disposition_to_default_score,
)
from dungeon_master_os.battlemap import BIOME_CATALOG, generate_battlemap
from dungeon_master_os.config import campaigns_dir
from dungeon_master_os.dice import roll_polyhedral
from dungeon_master_os.heroes import build_hero

BIOME_CREATURE_TEMPLATES: dict[str, dict[str, Any]] = {
    "sunken_obsidian_crypt": {
        "npcs": [
            {
                "id": "npc_vaelen",
                "name": "Vaelen the Blind Ossuary Keeper",
                "title": "Custodian of the Silent Legion",
                "symbol": "🕯️",
                "color": "#c084fc",
                "portrait": "/static/assets/portraits/hero_wizard.jpg",
                "miniature": "wizard",
                "x": 4,
                "y": 4,
                "disposition": "Suspicious",
                "disposition_score": -18,
                "voice_quirk": "Raspy, rhythmic whisper punctuated by the clinking of brass censor chains",
                "secret_motive": "Knows the secret command phrase ('MORROW-ECLIPSE') that deactivates the Obsidian Bone-Golem's armor plating.",
                "greeting": "Who treads upon the basalt of the fallen? Speak your vow or turn back!",
                "memory_log": [
                    {
                        "time": "00:00:01",
                        "event": "Heard heavy footsteps enter the Vestibule of Weeping Basalt",
                        "shift": "Suspicious (-18)",
                        "disposition": "Suspicious",
                    }
                ],
            },
            {
                "id": "npc_seraphina",
                "name": "Echo of Lady Seraphina",
                "title": "Bound Astral Remnant",
                "symbol": "👑",
                "color": "#38bdf8",
                "portrait": "/static/assets/portraits/hero_rogue.jpg",
                "miniature": "rogue",
                "x": 11,
                "y": 2,
                "disposition": "Neutral",
                "disposition_score": 10,
                "voice_quirk": "Melodic, dual-toned voice that echoes like cathedral glass",
                "secret_motive": "Guards the hidden Crown of Sunken Ash in the southeastern sanctum chest and seeks an honorable champion.",
                "greeting": "Three centuries have passed since a living soul crossed the Hall of Mirrors.",
                "memory_log": [
                    {
                        "time": "00:00:01",
                        "event": "Manifested beside the Violet Soul-Brazier",
                        "shift": "Neutral (+10)",
                        "disposition": "Neutral",
                    }
                ],
            },
        ],
        "monsters": [
            {
                "id": "mon_bone_golem",
                "name": "Obsidian Bone-Golem",
                "symbol": "💀",
                "portrait": "/static/assets/portraits/monster_golem.jpg",
                "miniature": "golem",
                "x": 11,
                "y": 8,
                "hp": 32,
                "max_hp": 32,
                "ac": 14,
                "initiative": 11,
                "attack_bonus": 5,
                "damage": 6,
                "range_ft": 15,
                "attack_name": "Basalt Cleaver Slam",
                "xp_reward": 600,
                "gold_reward": 95,
                "loot_drop": {
                    "id": "crown_sunken_ash",
                    "name": "Crown of Sunken Ash",
                    "type": "armor",
                    "equipped": False,
                    "bonus_ac": 2,
                    "qty": 1,
                    "desc": "Relic diadem forged from volcanic glass (+2 AC).",
                },
            },
            {
                "id": "mon_ashen_wraith",
                "name": "Malakor the Lich King",
                "symbol": "👻",
                "portrait": "/static/assets/portraits/monster_lich.jpg",
                "miniature": "lich",
                "x": 5,
                "y": 8,
                "hp": 24,
                "max_hp": 24,
                "ac": 13,
                "initiative": 14,
                "attack_bonus": 4,
                "damage": 5,
                "range_ft": 25,
                "attack_name": "Soul-Chill Necrotic Bolt",
                "xp_reward": 450,
                "gold_reward": 65,
                "loot_drop": {
                    "id": "wraith_essence_vial",
                    "name": "Phial of Condensed Starlight",
                    "type": "potion",
                    "equipped": False,
                    "heal_amount": 16,
                    "mana_amount": 8,
                    "qty": 1,
                    "desc": "Restores 16 HP and 8 Mana.",
                },
            },
            {
                "id": "mon_ashfang_dragon",
                "name": "Ignisaur, Ancient Red Dragon",
                "symbol": "🐉",
                "portrait": "/static/assets/portraits/monster_dragon.jpg",
                "miniature": "dragon",
                "x": 12,
                "y": 4,
                "hp": 45,
                "max_hp": 45,
                "ac": 16,
                "initiative": 16,
                "attack_bonus": 6,
                "damage": 8,
                "range_ft": 30,
                "attack_name": "Cataclysmic Hellfire Breath",
                "xp_reward": 900,
                "gold_reward": 180,
                "loot_drop": {
                    "id": "draconic_heartstone",
                    "name": "Heartstone of Ignisaur",
                    "type": "weapon",
                    "equipped": False,
                    "damage_dice": "2d12+5",
                    "attack_ability": "STR",
                    "bonus_ac": 1,
                    "qty": 1,
                    "desc": "Legendary dragonfire relic (+1 AC, 2d12+5 fire damage).",
                },
            },
        ],
    },
    "clockwork_astral_spire": {
        "npcs": [
            {
                "id": "npc_twill",
                "name": "Arch-Horologist Twill",
                "title": "Keeper of the Grand Orrery",
                "symbol": "🔭",
                "color": "#38bdf8",
                "portrait": "/static/assets/portraits/hero_wizard.jpg",
                "miniature": "wizard",
                "x": 4,
                "y": 3,
                "disposition": "Neutral",
                "disposition_score": 8,
                "voice_quirk": "Rapid-fire staccato speech, constantly checking a 7-handed pocket chronometer",
                "secret_motive": "Hid the Master Winding Key inside the northern escapement chest to stop the rogue Chrono-Sentinel.",
                "greeting": "Tick-tock! You're 4.7 seconds late! State your theorem before the pendulum swings!",
                "memory_log": [
                    {
                        "time": "00:00:01",
                        "event": "Calibrated the Orrery Landing Deck upon hero arrival",
                        "shift": "Neutral (+8)",
                        "disposition": "Neutral",
                    }
                ],
            },
            {
                "id": "npc_cipher_nine",
                "name": "Cipher-Automaton Nine",
                "title": "Sentient Brass Navigator",
                "symbol": "🤖",
                "color": "#34d399",
                "portrait": "/static/assets/portraits/hero_paladin.jpg",
                "miniature": "paladin",
                "x": 10,
                "y": 3,
                "disposition": "Friendly",
                "disposition_score": 32,
                "voice_quirk": "Warm baritone accompanied by melodic music-box chimes",
                "secret_motive": "Will gladly join as a Sworn Ally if promised freedom from the Spire's memory wipe protocol.",
                "greeting": "Greetings, Chronomancer. My optical sensors detect high-voltage temporal anomalies ahead.",
                "memory_log": [
                    {
                        "time": "00:00:01",
                        "event": "Recognized arcane resonance from the hero's staff",
                        "shift": "Friendly (+32)",
                        "disposition": "Friendly",
                    }
                ],
            },
        ],
        "monsters": [
            {
                "id": "mon_chrono_sentinel",
                "name": "Chrono-Sentinel Mk IV",
                "symbol": "⚙️",
                "portrait": "/static/assets/portraits/monster_golem.jpg",
                "miniature": "golem",
                "x": 11,
                "y": 9,
                "hp": 30,
                "max_hp": 30,
                "ac": 14,
                "initiative": 13,
                "attack_bonus": 5,
                "damage": 6,
                "range_ft": 25,
                "attack_name": "Aether-Arc Halberd",
                "xp_reward": 600,
                "gold_reward": 110,
                "loot_drop": {
                    "id": "core_chronos",
                    "name": "Singularity Core Pendulum",
                    "type": "weapon",
                    "equipped": False,
                    "damage_dice": "2d10+5",
                    "attack_ability": "INT",
                    "bonus_ac": 1,
                    "qty": 1,
                    "desc": "Masterwork astral focus (+1 AC, 2d10+5 damage).",
                },
            },
            {
                "id": "mon_void_drone",
                "name": "Xanathar Void-Eye Beholder",
                "symbol": "👁️",
                "portrait": "/static/assets/portraits/monster_beholder.jpg",
                "miniature": "beholder",
                "x": 4,
                "y": 8,
                "hp": 22,
                "max_hp": 22,
                "ac": 13,
                "initiative": 15,
                "attack_bonus": 4,
                "damage": 5,
                "range_ft": 25,
                "attack_name": "Disintegration Eye Ray",
                "xp_reward": 420,
                "gold_reward": 65,
                "loot_drop": None,
            },
        ],
    },
    "rustport_tavern_brawl": {
        "npcs": [
            {
                "id": "npc_skarn",
                "name": "Quartermaster Skarn",
                "title": "Ironhook Syndicate Broker",
                "symbol": "🏴‍☠️",
                "color": "#f59e0b",
                "portrait": "/static/assets/portraits/hero_paladin.jpg",
                "miniature": "paladin",
                "x": 5,
                "y": 3,
                "disposition": "Suspicious",
                "disposition_score": -20,
                "voice_quirk": "Gravelly sea-dog growl, tapping a gold doubloon across brass knuckles",
                "secret_motive": "Can be bribed with 25 gp or persuaded to hand over the Harbormaster's Strongroom Ledger without bloodshed.",
                "greeting": "This table's reserved for Ironhook captains. Either buy a round of gold or step aside!",
                "memory_log": [
                    {
                        "time": "00:00:01",
                        "event": "Eyed the hero suspiciously across the Salty Kraken Taproom",
                        "shift": "Suspicious (-20)",
                        "disposition": "Suspicious",
                    }
                ],
            },
            {
                "id": "npc_mira",
                "name": "Mira Voss, Void-Smuggler",
                "title": "Captain of the Star-Skiff 'Halcyon'",
                "symbol": "🧭",
                "color": "#38bdf8",
                "portrait": "/static/assets/portraits/hero_rogue.jpg",
                "miniature": "rogue",
                "x": 11,
                "y": 2,
                "disposition": "Friendly",
                "disposition_score": 35,
                "voice_quirk": "Quick-witted, conspiratorial wink with a slight celestial drawl",
                "secret_motive": "Waiting for an ally to clear the Rum Cellar so she can split the Syndicate's star-sapphire stash.",
                "greeting": "Psst! Over here by the hearth—watch out for the spilled ale slick near the cellar door.",
                "memory_log": [
                    {
                        "time": "00:00:01",
                        "event": "Tipped off the hero about the taproom ambush",
                        "shift": "Friendly (+35)",
                        "disposition": "Friendly",
                    }
                ],
            },
        ],
        "monsters": [
            {
                "id": "mon_ironhook_bruiser",
                "name": "Ironhook Golem Enforcer",
                "symbol": "⚓",
                "portrait": "/static/assets/portraits/monster_golem.jpg",
                "miniature": "golem",
                "x": 11,
                "y": 8,
                "hp": 28,
                "max_hp": 28,
                "ac": 13,
                "initiative": 12,
                "attack_bonus": 5,
                "damage": 6,
                "range_ft": 15,
                "attack_name": "Grapnel Chain Hook",
                "xp_reward": 550,
                "gold_reward": 120,
                "loot_drop": {
                    "id": "admiral_flintlock",
                    "name": "Aether-Spark Dragoon Pistol",
                    "type": "weapon",
                    "equipped": False,
                    "damage_dice": "2d8+5",
                    "attack_ability": "DEX",
                    "bonus_ac": 0,
                    "qty": 1,
                    "desc": "Twin-barreled arcane flintlock pistol.",
                },
            },
            {
                "id": "mon_bilge_hound",
                "name": "Cellar Beholder Horror",
                "symbol": "👁️",
                "portrait": "/static/assets/portraits/monster_beholder.jpg",
                "miniature": "beholder",
                "x": 5,
                "y": 8,
                "hp": 18,
                "max_hp": 18,
                "ac": 12,
                "initiative": 14,
                "attack_bonus": 4,
                "damage": 4,
                "range_ft": 15,
                "attack_name": "Paralyzing Eye Ray",
                "xp_reward": 340,
                "gold_reward": 50,
                "loot_drop": None,
            },
        ],
    },
}


def _creatures_for_biome(biome_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import copy

    if biome_id in BIOME_CREATURE_TEMPLATES:
        tpl = copy.deepcopy(BIOME_CREATURE_TEMPLATES[biome_id])
        return tpl["npcs"], tpl["monsters"]

    biome = BIOME_CATALOG.get(biome_id, BIOME_CATALOG["sunken_obsidian_crypt"])
    bword = biome["name"].split()[0]
    npcs = [
        {
            "id": f"npc_{biome_id}_warden",
            "name": f"Warden Lyra of the {bword}",
            "title": f"Keeper of {biome['name']}",
            "symbol": "🛡️",
            "color": "#38bdf8",
            "portrait": "/static/assets/portraits/hero_wizard.jpg",
            "miniature": "wizard",
            "x": 4,
            "y": 3,
            "disposition": "Neutral",
            "disposition_score": 10,
            "voice_quirk": "Clear, resonant cadence with old-world formality",
            "secret_motive": f"Knows the safe route through the {biome['hazard_name']} and guards the sanctum cipher.",
            "greeting": f"Welcome to the {biome['name']}. Tread carefully—the ancient wards are awake.",
            "memory_log": [
                {
                    "time": "00:00:01",
                    "event": f"Encountered hero in {biome['room_names'][0]}",
                    "shift": "Neutral (+10)",
                    "disposition": "Neutral",
                }
            ],
        },
        {
            "id": f"npc_{biome_id}_broker",
            "name": f"Zarek the {bword} Delver",
            "title": "Relic Seeker & Guide",
            "symbol": "🧭",
            "color": "#f59e0b",
            "portrait": "/static/assets/portraits/hero_rogue.jpg",
            "miniature": "rogue",
            "x": 11,
            "y": 2,
            "disposition": "Suspicious",
            "disposition_score": -15,
            "voice_quirk": "Husky, cautious tone, glancing toward the shadowed doors",
            "secret_motive": "Will trade the vault combination in exchange for a 25 gp bribe or an oath of shared loot.",
            "greeting": "Hold! Another treasure hunter? Prove you aren't with the syndicate!",
            "memory_log": [
                {
                    "time": "00:00:01",
                    "event": "Guarded the northern chamber chest",
                    "shift": "Suspicious (-15)",
                    "disposition": "Suspicious",
                }
            ],
        },
    ]
    monsters = [
        {
            "id": f"mon_{biome_id}_boss",
            "name": f"{bword} Ancient Red Dragon",
            "symbol": "🐉",
            "portrait": "/static/assets/portraits/monster_dragon.jpg",
            "miniature": "dragon",
            "x": 11,
            "y": 8,
            "hp": 36,
            "max_hp": 36,
            "ac": 15,
            "initiative": 13,
            "attack_bonus": 5,
            "damage": 7,
            "range_ft": 25,
            "attack_name": f"{bword} Hellfire Nova",
            "xp_reward": 700,
            "gold_reward": 120,
            "loot_drop": biome["loot_pool"][0],
        },
        {
            "id": f"mon_{biome_id}_scout",
            "name": f"{bword} Eye-Tyrant Beholder",
            "symbol": "👁️",
            "portrait": "/static/assets/portraits/monster_beholder.jpg",
            "miniature": "beholder",
            "x": 5,
            "y": 8,
            "hp": 20,
            "max_hp": 20,
            "ac": 13,
            "initiative": 14,
            "attack_bonus": 4,
            "damage": 5,
            "range_ft": 20,
            "attack_name": "Arcane Eye Beam",
            "xp_reward": 380,
            "gold_reward": 55,
            "loot_drop": None,
        },
    ]
    return npcs, monsters


def create_campaign(
    title: str,
    biome_id: str = "sunken_obsidian_crypt",
    hero_preset_id: str = "kaelen_paladin",
    campaign_id: str | None = None,
    synopsis: str = "",
    hero_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cid = campaign_id or f"camp_{int(time.time())}_{biome_id[:8]}"
    hero = build_hero(hero_preset_id, overrides=hero_overrides)
    bmap = generate_battlemap(biome_id=biome_id)
    npcs, monsters = _creatures_for_biome(biome_id)

    for n in npcs:
        if "disposition_score" not in n:
            n["disposition_score"] = disposition_to_default_score(n.get("disposition", "Neutral"))

    opening_roll = roll_polyhedral(
        sides=20,
        count=1,
        modifier=int(hero["modifiers"].get("WIS", 1)) + int(hero["proficiency_bonus"]),
        dc=12,
        label="Opening Perception Check (WIS) vs DC 12",
        forced_natural=16,
    )

    room_0 = bmap["rooms"][0]["name"]
    opening_narrative = (
        f"🏰 **ACT I — {title.upper()} ({bmap['biome_name']})**\n\n"
        f"**{hero['name']}** (*Level {hero['level']} {hero['ancestry']} {hero['class_name']}*) steps into **{room_0}** at coordinates `(2, 3)`. "
        f"{WorldbuilderGMAgent.SENSORY_PALETTES.get(biome_id, ['Ancient magic hums through the stone.'])[0]}\n\n"
        f"- **NPC Presence:** **{npcs[0]['name']}** (*{npcs[0]['disposition']}*) watches from `({npcs[0]['x']}, {npcs[0]['y']})`: *\"{npcs[0]['greeting']}\"*  \n"
        f"- **Tactical Threat:** **{monsters[0]['name']}** (`HP {monsters[0]['hp']}/{monsters[0]['max_hp']}`, `AC {monsters[0]['ac']}`) and **{monsters[1]['name']}** prowl the deeper chambers."
    )

    campaign: dict[str, Any] = {
        "id": cid,
        "title": title,
        "synopsis": synopsis or bmap["biome_subtitle"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hero": hero,
        "battlemap": bmap,
        "npcs": npcs,
        "monsters": monsters,
        "combat": {},
        "dice_history": [opening_roll],
        "chronicle": [
            {
                "id": f"turn_init_{cid}",
                "timestamp": time.strftime("%H:%M:%S"),
                "player_action": f"Enter {room_0} & survey the tactical battlemap",
                "action_type": "explore",
                "room_name": room_0,
                "narrative": opening_narrative,
                "agents": {
                    "worldbuilder": {
                        "name": "Worldbuilder & Narrative GM",
                        "summary": f"Initialized {bmap['biome_name']} ({bmap['width']}x{bmap['height']} grid, 5 ft/tile).",
                        "provider": "offline",
                    },
                    "rules_lawyer": {
                        "name": "Rules Lawyer & D20 Mechanics",
                        "verdict": f"SUCCESS ({opening_roll['total']} vs DC 12)",
                        "summary": f"Perception check d20={opening_roll['natural']} + mod = {opening_roll['total']} vs DC 12.",
                        "ability": "WIS",
                        "skill": "Perception",
                        "dc": 12,
                        "roll": opening_roll,
                    },
                    "npc_actor": {
                        "name": "NPC Actor & Relationship Memory",
                        "npc_name": npcs[0]["name"],
                        "disposition": npcs[0]["disposition"],
                        "delta": 0,
                        "dialogue": npcs[0]["greeting"],
                        "summary": f"{npcs[0]['name']} ({npcs[0]['disposition']}) & {npcs[1]['name']} ({npcs[1]['disposition']}) loaded with persistent memory.",
                    },
                    "tactical_director": {
                        "name": "Tactical Encounter Director",
                        "round": 1,
                        "damage_dealt": 0,
                        "damage_taken": 0,
                        "loot_dropped": [],
                        "summary": f"Initiative rolled for {hero['name']} and {len(monsters)} hostile creatures.",
                    },
                },
            }
        ],
        "suggested_actions": [],
    }
    TacticalDirectorAgent.sync_initiative(campaign)
    campaign["suggested_actions"] = WorldbuilderGMAgent.suggest_actions(campaign)
    return campaign


SHOWCASE_CAMPAIGN_SPECS: list[dict[str, str]] = [
    {
        "campaign_id": "camp_sunken_crypt",
        "title": "The Crown of Sunken Ash",
        "biome_id": "sunken_obsidian_crypt",
        "hero_preset_id": "kaelen_paladin",
        "synopsis": "Descend into the Sunken Obsidian Crypt, parley with Vaelen the Blind Ossuary Keeper, and reclaim the Crown of Sunken Ash from the Obsidian Bone-Golem.",
    },
    {
        "campaign_id": "camp_astral_spire",
        "title": "Heist at the Clockwork Astral Spire",
        "biome_id": "clockwork_astral_spire",
        "hero_preset_id": "eldrin_chronomancer",
        "synopsis": "Navigate whirring brass escapements and temporal runes high in the Astral Spire, ally with Cipher-Automaton Nine, and shut down the rogue Chrono-Sentinel Mk IV.",
    },
    {
        "campaign_id": "camp_rustport_brawl",
        "title": "Mutiny on the Rustport Star-Galleon",
        "biome_id": "rustport_tavern_brawl",
        "hero_preset_id": "vex_rogue",
        "synopsis": "Survive a dockside ambush at the Salty Kraken Taproom, bribe or outwit Quartermaster Skarn, and seize the Syndicate's strongroom chest.",
    },
]


def save_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    cid = campaign["id"]
    path = campaigns_dir() / f"{cid}.json"
    campaign["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    return campaign


def load_campaign(campaign_id: str) -> dict[str, Any] | None:
    path = campaigns_dir() / f"{campaign_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def ensure_showcase_campaigns() -> list[dict[str, Any]]:
    """Ensure the 3 pre-loaded playable campaigns exist on disk with 3D miniature & portrait metadata."""
    for spec in SHOWCASE_CAMPAIGN_SPECS:
        path = campaigns_dir() / f"{spec['campaign_id']}.json"
        needs_create = not path.is_file()
        if not needs_create:
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if not existing.get("hero", {}).get("portrait"):
                    needs_create = True
            except Exception:
                needs_create = True
        if needs_create:
            camp = create_campaign(
                title=spec["title"],
                biome_id=spec["biome_id"],
                hero_preset_id=spec["hero_preset_id"],
                campaign_id=spec["campaign_id"],
                synopsis=spec["synopsis"],
            )
            save_campaign(camp)
    return list_campaigns()


def reset_showcase_campaign(campaign_id: str) -> dict[str, Any]:
    spec = next((s for s in SHOWCASE_CAMPAIGN_SPECS if s["campaign_id"] == campaign_id), None)
    if spec:
        camp = create_campaign(
            title=spec["title"],
            biome_id=spec["biome_id"],
            hero_preset_id=spec["hero_preset_id"],
            campaign_id=spec["campaign_id"],
            synopsis=spec["synopsis"],
        )
        return save_campaign(camp)
    existing = load_campaign(campaign_id)
    if not existing:
        raise ValueError(f"Campaign {campaign_id!r} not found.")
    camp = create_campaign(
        title=existing["title"],
        biome_id=existing["battlemap"]["biome_id"],
        hero_preset_id=existing["hero"]["id"],
        campaign_id=campaign_id,
        synopsis=existing.get("synopsis", ""),
    )
    return save_campaign(camp)


def list_campaigns() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    priority = {"camp_sunken_crypt": 0, "camp_astral_spire": 1, "camp_rustport_brawl": 2}
    paths = sorted(
        campaigns_dir().glob("*.json"),
        key=lambda p: (priority.get(p.stem, 99), p.name),
    )
    for p in paths:
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            out.append(
                {
                    "id": c["id"],
                    "title": c["title"],
                    "synopsis": c.get("synopsis", ""),
                    "biome_id": c["battlemap"]["biome_id"],
                    "biome_name": c["battlemap"]["biome_name"],
                    "hero_name": c["hero"]["name"],
                    "hero_class": c["hero"]["class_name"],
                    "hero_level": c["hero"]["level"],
                    "turns_count": len(c.get("chronicle", [])),
                    "updated_at": c.get("updated_at", ""),
                }
            )
        except Exception:
            continue
    return out


def export_chronicle_markdown(campaign: dict[str, Any]) -> str:
    """Export the full adventure chronicle, hero sheet, NPC relationships, and roll history as Markdown."""
    h = campaign["hero"]
    bmap = campaign["battlemap"]
    lines = [
        f"# 📜 {campaign['title']} — Adventure Chronicle",
        "",
        f"- **Campaign ID:** `{campaign['id']}`",
        f"- **Biome:** {bmap['biome_name']} (`{bmap['width']}x{bmap['height']}` grid, `5 ft/tile`)",
        f"- **Hero:** **{h['name']}** (Level {h['level']} {h['ancestry']} {h['class_name']})",
        f"- **Vitals:** HP `{h['hp']}/{h['max_hp']}` | Mana `{h['mana']}/{h['max_mana']}` | AC `{h['ac']}` | Gold `{h['gold']} gp` | XP `{h['xp']}/{h['xp_next']}`",
        f"- **Ability Scores:** " + ", ".join(f"{k} {v} ({h['modifiers'][k]:+d})" for k, v in h["abilities"].items()),
        "",
        "## 🤝 NPC Relationships & Persistent Memory",
        "",
    ]
    for npc in campaign.get("npcs", []):
        lines.append(f"### {npc['name']} — *{npc.get('title', '')}*")
        lines.append(f"- **Disposition:** **{npc['disposition']}** (`{npc.get('disposition_score', 0):+d}`)")
        lines.append(f"- **Voice Quirk:** {npc.get('voice_quirk', '')}")
        motive = npc.get("secret_motive") if npc.get("disposition") in ("Friendly", "Sworn Ally") else "Hidden until Friendly or Sworn Ally"
        lines.append(f"- **Secret Motive:** {motive}")
        for mem in npc.get("memory_log", []):
            lines.append(f"  - `[{mem['time']}]` {mem['event']} → *{mem['shift']}*")
        lines.append("")

    lines.append("## ⚔️ Adventure Turn Log")
    lines.append("")
    for idx, entry in enumerate(campaign.get("chronicle", []), start=1):
        lines.append(f"### Turn {idx} (`{entry.get('timestamp', '')}`) — {entry.get('room_name', '')}")
        lines.append(f"**Player Action:** `{entry.get('player_action', '')}`")
        lines.append("")
        lines.append(entry.get("narrative", ""))
        lines.append("")
        ag = entry.get("agents", {})
        rl = ag.get("rules_lawyer", {})
        if rl.get("verdict"):
            lines.append(f"- **Rules Lawyer Agent:** `{rl['verdict']}` — {rl.get('summary', '')}")
        na = ag.get("npc_actor", {})
        if na.get("summary"):
            lines.append(f"- **NPC Actor Agent:** {na['summary']}")
        td = ag.get("tactical_director", {})
        if td.get("summary"):
            lines.append(f"- **Tactical Encounter Director:** {td['summary']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def export_chronicle_html(campaign: dict[str, Any]) -> str:
    """Export a standalone styled dark-gold fantasy HTML Adventure Log."""
    h = campaign["hero"]
    bmap = campaign["battlemap"]
    turns_html = []
    for idx, entry in enumerate(campaign.get("chronicle", []), start=1):
        ag = entry.get("agents", {})
        rl = ag.get("rules_lawyer", {})
        turns_html.append(
            f"""
            <article class="turn-card">
              <div class="turn-head">
                <span class="turn-num">Turn #{idx}</span>
                <span class="turn-room">{html.escape(str(entry.get("room_name", "")))}</span>
                <span class="turn-time">{html.escape(str(entry.get("timestamp", "")))}</span>
              </div>
              <div class="turn-action"><strong>Action:</strong> {html.escape(str(entry.get("player_action", "")))}</div>
              <div class="turn-body">{html.escape(str(entry.get("narrative", ""))).replace(chr(10), "<br/>")}</div>
              <div class="turn-agents">
                <span class="badge">🎲 {html.escape(str(rl.get("verdict", "Mechanics Resolved")))}</span>
                <span class="badge">⚔️ {html.escape(str(ag.get("tactical_director", {}).get("summary", "")))}</span>
              </div>
            </article>
            """
        )

    npc_html = []
    for n in campaign.get("npcs", []):
        npc_html.append(
            f"<li><strong>{html.escape(n['name'])}</strong> — <em>{html.escape(n['disposition'])}</em> "
            f"(Score: {n.get('disposition_score', 0):+d}) — {html.escape(n.get('voice_quirk', ''))}</li>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(campaign['title'])} — Dungeon Master OS Chronicle</title>
  <style>
    body {{ background:#0b0d14; color:#e2e8f0; font-family: Georgia, serif; max-width:920px; margin:32px auto; padding:0 20px; line-height:1.6; }}
    h1, h2 {{ color:#f59e0b; border-bottom:1px solid #2e364f; padding-bottom:8px; }}
    .meta {{ background:#131724; border:1px solid #2a3149; border-radius:10px; padding:16px; margin-bottom:24px; }}
    .turn-card {{ background:#141927; border:1px solid #283048; border-left:4px solid #f59e0b; border-radius:8px; padding:16px; margin-bottom:16px; }}
    .turn-head {{ display:flex; gap:12px; font-family:monospace; color:#94a3b8; font-size:0.9rem; margin-bottom:8px; }}
    .turn-num {{ color:#f59e0b; font-weight:bold; }}
    .turn-action {{ background:#0d111c; padding:8px 12px; border-radius:6px; margin-bottom:10px; font-family:sans-serif; }}
    .turn-agents {{ margin-top:12px; display:flex; flex-wrap:wrap; gap:8px; font-family:sans-serif; font-size:0.82rem; }}
    .badge {{ background:#1e293b; color:#cbd5e1; padding:4px 10px; border-radius:999px; }}
  </style>
</head>
<body>
  <h1>📜 {html.escape(campaign['title'])} — Adventure Chronicle</h1>
  <div class="meta">
    <p><strong>Biome:</strong> {html.escape(bmap['biome_name'])} ({bmap['width']}×{bmap['height']} Grid, 5 ft/tile)</p>
    <p><strong>Hero:</strong> {html.escape(h['name'])} — Level {h['level']} {html.escape(h['ancestry'])} {html.escape(h['class_name'])}</p>
    <p><strong>Vitals:</strong> HP {h['hp']}/{h['max_hp']} | Mana {h['mana']}/{h['max_mana']} | AC {h['ac']} | Gold {h['gold']} gp</p>
  </div>
  <h2>🤝 NPC Disposition Roster</h2>
  <ul>{''.join(npc_html)}</ul>
  <h2>⚔️ Chronicle Entries</h2>
  {''.join(turns_html)}
</body>
</html>"""
