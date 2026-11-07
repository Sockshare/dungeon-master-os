"""Hero Builder, Character Sheet, Inventory & Spellbook Engine."""

from __future__ import annotations

import copy
from typing import Any

ABILITY_KEYS: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

SKILL_TO_ABILITY: dict[str, str] = {
    "Athletics": "STR",
    "Acrobatics": "DEX",
    "Stealth": "DEX",
    "Sleight of Hand": "DEX",
    "Arcana": "INT",
    "Investigation": "INT",
    "History": "INT",
    "Engineering": "INT",
    "Perception": "WIS",
    "Insight": "WIS",
    "Survival": "WIS",
    "Medicine": "WIS",
    "Persuasion": "CHA",
    "Intimidation": "CHA",
    "Deception": "CHA",
}


def ability_mod(score: int) -> int:
    return (int(score) - 10) // 2


def compute_modifiers(abilities: dict[str, int]) -> dict[str, int]:
    return {k: ability_mod(abilities.get(k, 10)) for k in ABILITY_KEYS}


HERO_PRESETS: dict[str, dict[str, Any]] = {
    "eldrin_chronomancer": {
        "id": "eldrin_chronomancer",
        "name": "Eldrin the Chronomancer",
        "ancestry": "High-Elf",
        "class_name": "Chronurgy Wizard",
        "level": 3,
        "xp": 900,
        "xp_next": 2700,
        "hp": 26,
        "max_hp": 26,
        "mana": 18,
        "max_mana": 18,
        "base_ac": 13,
        "ac": 15,
        "speed_ft": 30,
        "vision_radius": 5,
        "gold": 145,
        "proficiency_bonus": 2,
        "token_symbol": "⏳",
        "token_color": "#38bdf8",
        "portrait_badge": "CHRONO",
        "portrait": "/static/assets/portraits/hero_wizard.jpg",
        "miniature": "wizard",
        "backstory": "An exiled Astral Spire scholar who bends fractured seconds to rewrite lethal mistakes.",
        "abilities": {"STR": 9, "DEX": 15, "CON": 14, "INT": 18, "WIS": 14, "CHA": 12},
        "proficient_skills": ["Arcana", "Investigation", "History", "Perception"],
        "spells": [
            {
                "id": "temporal_rift_bolt",
                "name": "Temporal Rift Bolt",
                "cost_mana": 3,
                "damage_dice": "2d8+4",
                "ability": "INT",
                "range_ft": 60,
                "vfx": "lightning",
                "desc": "Fires a lance of fractured time that deals 2d8+4 force damage and slows the target.",
            },
            {
                "id": "chronal_stasis",
                "name": "Chronal Fireball",
                "cost_mana": 4,
                "damage_dice": "2d10+4",
                "ability": "INT",
                "range_ft": 45,
                "vfx": "fireball",
                "desc": "Detonates a blazing sphere of compressed solar time dealing 2d10+4 fire & force damage.",
            },
            {
                "id": "aegis_of_rewind",
                "name": "Aegis of Rewind",
                "cost_mana": 3,
                "heal_dice": "2d6+4",
                "ability": "INT",
                "range_ft": 15,
                "vfx": "heal",
                "desc": "Rewinds recent wounds, restoring 2d6+4 HP and granting +2 AC for the scene.",
            },
        ],
        "inventory": [
            {
                "id": "staff_aethel",
                "name": "Hourglass Staff of Aethel",
                "type": "weapon",
                "equipped": True,
                "damage_dice": "1d8+4",
                "attack_ability": "INT",
                "bonus_ac": 0,
                "qty": 1,
                "desc": "Arcane focus quarterstaff etched with glowing silver sand.",
            },
            {
                "id": "astral_robes",
                "name": "Astral Silk Robes",
                "type": "armor",
                "equipped": True,
                "bonus_ac": 2,
                "qty": 1,
                "desc": "Starlight-threaded vestments that shimmer with protective wards (+2 AC).",
            },
            {
                "id": "potion_healing",
                "name": "Greater Crimson Potion",
                "type": "potion",
                "equipped": False,
                "heal_amount": 14,
                "mana_amount": 4,
                "qty": 2,
                "desc": "Restores 14 HP and 4 Mana when quaffed.",
            },
            {
                "id": "chrono_tonic",
                "name": "Chrono-Tonic Vial",
                "type": "potion",
                "equipped": False,
                "heal_amount": 6,
                "mana_amount": 10,
                "qty": 2,
                "desc": "Restores 10 Mana and 6 HP with liquid starlight.",
            },
        ],
    },
    "kaelen_paladin": {
        "id": "kaelen_paladin",
        "name": "Kaelen the Oathbreaker Paladin",
        "ancestry": "Fallen Aasimar",
        "class_name": "Oathbreaker Vanguard",
        "level": 3,
        "xp": 900,
        "xp_next": 2700,
        "hp": 36,
        "max_hp": 36,
        "mana": 12,
        "max_mana": 12,
        "base_ac": 14,
        "ac": 18,
        "speed_ft": 30,
        "vision_radius": 4,
        "gold": 120,
        "proficiency_bonus": 2,
        "token_symbol": "⚔️",
        "token_color": "#f59e0b",
        "portrait_badge": "PALADIN",
        "portrait": "/static/assets/portraits/hero_paladin.jpg",
        "miniature": "paladin",
        "backstory": "Once sworn to the Solar Throne, Kaelen shattered his vows to save a condemned legion from the Sunken Crypt.",
        "abilities": {"STR": 18, "DEX": 11, "CON": 16, "INT": 10, "WIS": 12, "CHA": 16},
        "proficient_skills": ["Athletics", "Intimidation", "Persuasion", "Insight"],
        "spells": [
            {
                "id": "abyssal_smite",
                "name": "Abyssal Smite",
                "cost_mana": 3,
                "damage_dice": "2d10+4",
                "ability": "STR",
                "range_ft": 10,
                "vfx": "fireball",
                "desc": "Wreathes Soulrender in crimson eclipse fire for a devastating 2d10+4 strike.",
            },
            {
                "id": "dreadful_aspect",
                "name": "Dreadful Aspect",
                "cost_mana": 4,
                "damage_dice": "2d6+3",
                "ability": "CHA",
                "range_ft": 30,
                "vfx": "lightning",
                "desc": "Unleashes an aura of sovereign dread that batters nearby foes and rattles morale.",
            },
            {
                "id": "shadowed_hands",
                "name": "Lay on Hands",
                "cost_mana": 3,
                "heal_dice": "2d8+3",
                "ability": "CHA",
                "range_ft": 5,
                "vfx": "heal",
                "desc": "Calls down a pillar of golden celestial light, restoring 2d8+3 HP.",
            },
        ],
        "inventory": [
            {
                "id": "soulrender_sword",
                "name": "Soulrender Greatsword",
                "type": "weapon",
                "equipped": True,
                "damage_dice": "2d6+4",
                "attack_ability": "STR",
                "bonus_ac": 0,
                "qty": 1,
                "desc": "Heavy obsidian-forged greatsword humming with twilight runes.",
            },
            {
                "id": "obsidian_plate",
                "name": "Obsidian Half-Plate",
                "type": "armor",
                "equipped": True,
                "bonus_ac": 4,
                "qty": 1,
                "desc": "Articulated black steel armor (+4 AC).",
            },
            {
                "id": "potion_healing",
                "name": "Greater Crimson Potion",
                "type": "potion",
                "equipped": False,
                "heal_amount": 14,
                "mana_amount": 4,
                "qty": 2,
                "desc": "Restores 14 HP and 4 Mana when quaffed.",
            },
        ],
    },
    "vex_rogue": {
        "id": "vex_rogue",
        "name": "Vex the Shadow Rogue",
        "ancestry": "Tiefling",
        "class_name": "Phantom Assassin",
        "level": 3,
        "xp": 900,
        "xp_next": 2700,
        "hp": 29,
        "max_hp": 29,
        "mana": 14,
        "max_mana": 14,
        "base_ac": 14,
        "ac": 16,
        "speed_ft": 35,
        "vision_radius": 5,
        "gold": 190,
        "proficiency_bonus": 2,
        "token_symbol": "🗡️",
        "token_color": "#a855f7",
        "portrait_badge": "ROGUE",
        "portrait": "/static/assets/portraits/hero_rogue.jpg",
        "miniature": "rogue",
        "backstory": "A velvet-gloved infiltrator from Rustport who walks through locked vaults and tavern brawls alike.",
        "abilities": {"STR": 10, "DEX": 18, "CON": 13, "INT": 14, "WIS": 13, "CHA": 15},
        "proficient_skills": ["Stealth", "Acrobatics", "Sleight of Hand", "Deception", "Perception"],
        "spells": [
            {
                "id": "crimson_coup",
                "name": "Crimson Coup de Grâce",
                "cost_mana": 3,
                "damage_dice": "3d6+4",
                "ability": "DEX",
                "range_ft": 20,
                "vfx": "lightning",
                "desc": "Shadow-steps behind a target for a lethal 3d6+4 sneak strike.",
            },
            {
                "id": "venomous_whisper",
                "name": "Infernal Hellfire Bomb",
                "cost_mana": 2,
                "damage_dice": "2d6+4",
                "ability": "DEX",
                "range_ft": 45,
                "vfx": "fireball",
                "desc": "Hurls an alchemical hellfire flask dealing 2d6+4 fire damage.",
            },
            {
                "id": "umbral_veil",
                "name": "Umbral Smoke Veil",
                "cost_mana": 3,
                "heal_dice": "2d6+3",
                "ability": "DEX",
                "range_ft": 10,
                "vfx": "heal",
                "desc": "Melts into shadow, patching wounds for 2d6+3 HP and evading traps.",
            },
        ],
        "inventory": [
            {
                "id": "twin_duskblades",
                "name": "Twin Duskblades",
                "type": "weapon",
                "equipped": True,
                "damage_dice": "1d8+4",
                "attack_ability": "DEX",
                "bonus_ac": 0,
                "qty": 1,
                "desc": "Paired finesse daggers that drink torchlight.",
            },
            {
                "id": "whisperweave_leather",
                "name": "Whisperweave Studded Leather",
                "type": "armor",
                "equipped": True,
                "bonus_ac": 2,
                "qty": 1,
                "desc": "Supple shadow-dyed leather armor (+2 AC).",
            },
            {
                "id": "potion_healing",
                "name": "Greater Crimson Potion",
                "type": "potion",
                "equipped": False,
                "heal_amount": 14,
                "mana_amount": 4,
                "qty": 2,
                "desc": "Restores 14 HP and 4 Mana when quaffed.",
            },
            {
                "id": "thieves_tools",
                "name": "Masterwork Thieves' Tools",
                "type": "gear",
                "equipped": True,
                "bonus_ac": 0,
                "qty": 1,
                "desc": "Grants +2 bonus to disarming traps and picking locks.",
            },
        ],
    },
    "bram_artificer": {
        "id": "bram_artificer",
        "name": "Bram the Runeforged Artificer",
        "ancestry": "Dragonborn / Forge-Kin",
        "class_name": "Storm-Forge Artificer",
        "level": 3,
        "xp": 900,
        "xp_next": 2700,
        "hp": 33,
        "max_hp": 33,
        "mana": 16,
        "max_mana": 16,
        "base_ac": 14,
        "ac": 17,
        "speed_ft": 25,
        "vision_radius": 5,
        "gold": 160,
        "proficiency_bonus": 2,
        "token_symbol": "⚙️",
        "token_color": "#10b981",
        "portrait_badge": "SORCERER",
        "portrait": "/static/assets/portraits/hero_sorcerer.jpg",
        "miniature": "sorcerer",
        "backstory": "Master draconic engineer of the Deep Foundry who channels living dragonfire & storm-runes through heavy ordnance.",
        "abilities": {"STR": 14, "DEX": 12, "CON": 16, "INT": 18, "WIS": 13, "CHA": 10},
        "proficient_skills": ["Engineering", "Investigation", "Arcana", "Athletics", "Medicine"],
        "spells": [
            {
                "id": "voltaic_arc_cannon",
                "name": "Voltaic Arc Cannon",
                "cost_mana": 3,
                "damage_dice": "2d8+4",
                "ability": "INT",
                "range_ft": 50,
                "desc": "Discharges a chained lightning beam dealing 2d8+4 lightning damage.",
            },
            {
                "id": "aether_turret",
                "name": "Aether Turret Overdrive",
                "cost_mana": 4,
                "damage_dice": "2d10+4",
                "ability": "INT",
                "range_ft": 40,
                "desc": "Deploys a clockwork ballista salvo across the room.",
            },
            {
                "id": "nanite_repair_pulse",
                "name": "Alchemical Repair Pulse",
                "cost_mana": 3,
                "heal_dice": "2d8+4",
                "ability": "INT",
                "range_ft": 15,
                "desc": "Releases restorative brass-nanites that heal 2d8+4 HP.",
            },
        ],
        "inventory": [
            {
                "id": "thundercoil_hammer",
                "name": "Thundercoil Warhammer",
                "type": "weapon",
                "equipped": True,
                "damage_dice": "1d10+4",
                "attack_ability": "INT",
                "bonus_ac": 0,
                "qty": 1,
                "desc": "Runeforged capacitor hammer that strikes with INT or STR.",
            },
            {
                "id": "exo_carapace",
                "name": "Clockwork Exo-Carapace",
                "type": "armor",
                "equipped": True,
                "bonus_ac": 3,
                "qty": 1,
                "desc": "Steam-assisted dwarven plate harness (+3 AC).",
            },
            {
                "id": "potion_healing",
                "name": "Alchemical Healing Draught",
                "type": "potion",
                "equipped": False,
                "heal_amount": 15,
                "mana_amount": 5,
                "qty": 2,
                "desc": "Restores 15 HP and 5 Mana when quaffed.",
            },
        ],
    },
}


def list_hero_presets() -> list[dict[str, Any]]:
    out = []
    for preset in HERO_PRESETS.values():
        h = copy.deepcopy(preset)
        h["modifiers"] = compute_modifiers(h["abilities"])
        out.append(h)
    return out


def build_hero(preset_id: str = "kaelen_paladin", overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base = copy.deepcopy(HERO_PRESETS.get(preset_id) or HERO_PRESETS["kaelen_paladin"])
    if overrides:
        for k in ("name", "ancestry", "class_name", "backstory", "token_symbol", "token_color"):
            if overrides.get(k):
                base[k] = overrides[k]
        if isinstance(overrides.get("abilities"), dict):
            for ab_k, ab_v in overrides["abilities"].items():
                if ab_k in ABILITY_KEYS:
                    base["abilities"][ab_k] = max(6, min(20, int(ab_v)))
    recalc_hero(base)
    return base


def recalc_hero(hero: dict[str, Any]) -> dict[str, Any]:
    hero["modifiers"] = compute_modifiers(hero.get("abilities", {}))
    lvl = max(1, int(hero.get("level", 1)))
    hero["proficiency_bonus"] = 2 + (lvl - 1) // 4
    bonus_ac = sum(
        int(item.get("bonus_ac", 0))
        for item in hero.get("inventory", [])
        if item.get("equipped")
    )
    dex_mod = max(0, hero["modifiers"].get("DEX", 0))
    base_ac = int(hero.get("base_ac", 12))
    hero["ac"] = base_ac + bonus_ac + min(2, dex_mod)
    hero["hp"] = max(0, min(int(hero.get("max_hp", 30)), int(hero.get("hp", 30))))
    hero["mana"] = max(0, min(int(hero.get("max_mana", 12)), int(hero.get("mana", 12))))
    return hero


def equip_Or_use_item(hero: dict[str, Any], item_id: str) -> tuple[dict[str, Any], str]:
    """Equip/unequip a weapon/armor or drink a potion from hero inventory."""
    inv = hero.get("inventory", [])
    target = next((it for it in inv if it.get("id") == item_id), None)
    if not target:
        return hero, f"Item '{item_id}' not found in inventory."

    itype = target.get("type", "gear")
    if itype == "potion":
        qty = int(target.get("qty", 1))
        if qty <= 0:
            return hero, f"No charges left in {target.get('name')}."
        heal = int(target.get("heal_amount", 12))
        mana = int(target.get("mana_amount", 4))
        old_hp, old_mana = hero["hp"], hero["mana"]
        hero["hp"] = min(hero["max_hp"], hero["hp"] + heal)
        hero["mana"] = min(hero["max_mana"], hero["mana"] + mana)
        target["qty"] = qty - 1
        if target["qty"] <= 0:
            hero["inventory"] = [it for it in inv if it.get("id") != item_id]
        recalc_hero(hero)
        return (
            hero,
            f"Drank {target['name']}: restored +{hero['hp'] - old_hp} HP and +{hero['mana'] - old_mana} Mana!",
        )

    if itype in ("weapon", "armor"):
        # If equipping a weapon or armor, unequip other items of same type
        new_state = not bool(target.get("equipped", False))
        if new_state:
            for it in inv:
                if it.get("type") == itype:
                    it["equipped"] = False
        target["equipped"] = new_state
        recalc_hero(hero)
        state_str = "Equipped" if new_state else "Unequipped"
        return hero, f"{state_str} {target['name']} (AC is now {hero['ac']})."

    target["equipped"] = not bool(target.get("equipped", False))
    recalc_hero(hero)
    return hero, f"Toggled {target['name']}."


def award_xp(hero: dict[str, Any], amount: int) -> tuple[dict[str, Any], bool, str]:
    """Grant XP and automatically level up when reaching xp_next."""
    hero["xp"] = int(hero.get("xp", 0)) + max(0, int(amount))
    leveled = False
    msg = f"+{amount} XP earned."
    while hero["xp"] >= int(hero.get("xp_next", 1000)):
        leveled = True
        hero["level"] = int(hero.get("level", 1)) + 1
        hero["xp_next"] = int(hero["xp_next"] * 1.8)
        hero["max_hp"] = int(hero.get("max_hp", 30)) + 7
        hero["hp"] = hero["max_hp"]
        hero["max_mana"] = int(hero.get("max_mana", 12)) + 3
        hero["mana"] = hero["max_mana"]
        # Boost primary stat slightly if under 20
        abilities = hero.get("abilities", {})
        best_stat = max(ABILITY_KEYS, key=lambda k: abilities.get(k, 10))
        if abilities.get(best_stat, 10) < 20:
            abilities[best_stat] = abilities.get(best_stat, 10) + 1
        recalc_hero(hero)
        msg = (
            f"LEVEL UP! {hero['name']} reached Level {hero['level']}! "
            f"Max HP increased to {hero['max_hp']}, Max Mana to {hero['max_mana']}, and {best_stat} rose to {abilities[best_stat]}!"
        )
    return hero, leveled, msg
