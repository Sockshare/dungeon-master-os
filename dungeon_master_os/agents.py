"""4-Agent Tabletop GM Engine for Dungeon Master OS.

Agents:
1. Worldbuilder & Narrative GM Agent
2. Rules Lawyer & D20 Mechanics Agent
3. NPC Actor Agent with Persistent Relationship Memory
4. Tactical Encounter Director
"""

from __future__ import annotations

import math
import random
import time
from typing import Any

import httpx

from dungeon_master_os.battlemap import current_room_name, shortest_walkable_path, tile_distance_ft, update_fog_of_war
from dungeon_master_os.config import DMOSSettings, load_settings
from dungeon_master_os.dice import DiceMode, parse_dice_expr, roll_polyhedral
from dungeon_master_os.heroes import SKILL_TO_ABILITY, award_xp, recalc_hero

DISPOSITION_TIERS: tuple[str, ...] = (
    "Hostile",
    "Suspicious",
    "Neutral",
    "Friendly",
    "Sworn Ally",
)


def score_to_disposition(score: int) -> str:
    s = max(-100, min(100, int(score)))
    if s <= -40:
        return "Hostile"
    if s <= -10:
        return "Suspicious"
    if s < 25:
        return "Neutral"
    if s < 65:
        return "Friendly"
    return "Sworn Ally"


def disposition_to_default_score(label: str) -> int:
    mapping = {
        "Hostile": -60,
        "Suspicious": -22,
        "Neutral": 5,
        "Friendly": 42,
        "Sworn Ally": 80,
    }
    return mapping.get(label, 5)


class RulesLawyerAgent:
    """Determines ability/skill checks, sets DC 10-20, resolves d20 + modifier, Nat 20 & Nat 1."""

    name = "Rules Lawyer & D20 Mechanics"

    @classmethod
    def classify_action(
        cls,
        action_text: str,
        action_type: str,
        hero: dict[str, Any],
        target_npc: dict[str, Any] | None,
        target_monster: dict[str, Any] | None,
    ) -> dict[str, Any]:
        txt = (action_text or "").lower()

        if action_type == "attack" or any(w in txt for w in ("attack", "strike", "slash", "shoot", "smite", "cleave", "stab")):
            weapon = next((it for it in hero.get("inventory", []) if it.get("type") == "weapon" and it.get("equipped")), None)
            ability = (weapon or {}).get("attack_ability", "STR")
            dc = int(target_monster.get("ac", 14)) if target_monster else 13
            dc = max(10, min(20, dc))
            return {
                "check_kind": "Attack Roll",
                "ability": ability,
                "skill": f"Weapon Attack ({(weapon or {}).get('name', 'Unarmed')})",
                "dc": dc,
                "damage_dice": (weapon or {}).get("damage_dice", "1d8+3"),
                "proficient": True,
            }

        if action_type == "spell" or any(w in txt for w in ("cast", "spell", "chronal", "temporal", "voltaic", "abyssal", "turret", "coup")):
            spells = hero.get("spells", [])
            chosen_spell = spells[0] if spells else {"name": "Arcane Bolt", "ability": "INT", "damage_dice": "2d8+4", "cost_mana": 2}
            for sp in spells:
                if sp["name"].lower() in txt or sp["id"].lower() in txt:
                    chosen_spell = sp
                    break
            ability = chosen_spell.get("ability", "INT")
            dc = int(target_monster.get("ac", 13)) if target_monster else 12
            dc = max(10, min(20, dc))
            return {
                "check_kind": "Spell Attack / Invocation",
                "ability": ability,
                "skill": f"Spellcasting ({chosen_spell['name']})",
                "dc": dc,
                "spell": chosen_spell,
                "damage_dice": chosen_spell.get("damage_dice"),
                "heal_dice": chosen_spell.get("heal_dice"),
                "proficient": True,
            }

        if any(w in txt for w in ("bribe", "gold", "pay", "persuade", "convince", "parley", "promise", "swear", "oath", "negotiate", "diplomacy", "ally")):
            base_dc = 12
            if target_npc:
                disp = target_npc.get("disposition", "Neutral")
                base_dc = {"Hostile": 17, "Suspicious": 14, "Neutral": 12, "Friendly": 10, "Sworn Ally": 10}.get(disp, 12)
            if any(w in txt for w in ("bribe", "gold", "promise", "swear", "oath")):
                base_dc = max(10, base_dc - 2)
            return {
                "check_kind": "Skill Check",
                "ability": "CHA",
                "skill": "Persuasion",
                "dc": max(10, min(20, base_dc)),
                "proficient": "Persuasion" in hero.get("proficient_skills", []),
            }

        if any(w in txt for w in ("threaten", "intimidate", "scare", "demand", "surrender", "cow")):
            return {
                "check_kind": "Skill Check",
                "ability": "CHA",
                "skill": "Intimidation",
                "dc": 14,
                "proficient": "Intimidation" in hero.get("proficient_skills", []),
            }

        if any(w in txt for w in ("deceive", "lie", "bluff", "disguise", "feint")):
            return {
                "check_kind": "Skill Check",
                "ability": "CHA",
                "skill": "Deception",
                "dc": 13,
                "proficient": "Deception" in hero.get("proficient_skills", []),
            }

        if any(w in txt for w in ("sneak", "stealth", "hide", "shadow", "creep")):
            return {
                "check_kind": "Skill Check",
                "ability": "DEX",
                "skill": "Stealth",
                "dc": 13,
                "proficient": "Stealth" in hero.get("proficient_skills", []),
            }

        if any(w in txt for w in ("disarm", "trap", "lock", "pick", "chest", "wire", "mechanism")):
            return {
                "check_kind": "Skill Check",
                "ability": "DEX",
                "skill": "Sleight of Hand",
                "dc": 13,
                "proficient": "Sleight of Hand" in hero.get("proficient_skills", []) or "Engineering" in hero.get("proficient_skills", []),
            }

        if any(w in txt for w in ("rune", "arcane", "decipher", "glyph", "chron", "portal", "study")):
            return {
                "check_kind": "Skill Check",
                "ability": "INT",
                "skill": "Arcana",
                "dc": 13,
                "proficient": "Arcana" in hero.get("proficient_skills", []),
            }

        if any(w in txt for w in ("search", "investigate", "inspect", "examine", "clue", "room", "look", "perceive", "scan")):
            skill = "Investigation" if "investigate" in txt or "examine" in txt else "Perception"
            ability = SKILL_TO_ABILITY.get(skill, "WIS")
            return {
                "check_kind": "Skill Check",
                "ability": ability,
                "skill": skill,
                "dc": 12,
                "proficient": skill in hero.get("proficient_skills", []),
            }

        if any(w in txt for w in ("climb", "leap", "jump", "shove", "force", "break", "lift")):
            return {
                "check_kind": "Skill Check",
                "ability": "STR",
                "skill": "Athletics",
                "dc": 13,
                "proficient": "Athletics" in hero.get("proficient_skills", []),
            }

        # Default versatile tabletop check
        best_ab = max(("STR", "DEX", "CON", "INT", "WIS", "CHA"), key=lambda k: hero.get("abilities", {}).get(k, 10))
        return {
            "check_kind": "Skill Check",
            "ability": best_ab,
            "skill": "Tactical Improvisation",
            "dc": 12,
            "proficient": True,
        }

    @classmethod
    def evaluate(
        cls,
        action_text: str,
        action_type: str,
        hero: dict[str, Any],
        target_npc: dict[str, Any] | None = None,
        target_monster: dict[str, Any] | None = None,
        dice_mode: DiceMode = "normal",
        player_d20_roll: int | None = None,
    ) -> dict[str, Any]:
        recalc_hero(hero)
        spec = cls.classify_action(action_text, action_type, hero, target_npc, target_monster)
        ability = spec["ability"]
        ab_mod = int(hero.get("modifiers", {}).get(ability, 0))
        prof = int(hero.get("proficiency_bonus", 2)) if spec.get("proficient") else 0
        # Check for masterwork tools bonus on lock/trap checks
        tool_bonus = 2 if spec["skill"] == "Sleight of Hand" and any(it.get("id") == "thieves_tools" for it in hero.get("inventory", [])) else 0
        total_mod = ab_mod + prof + tool_bonus
        dc = int(spec["dc"])

        roll_res = roll_polyhedral(
            sides=20,
            count=1,
            modifier=total_mod,
            mode=dice_mode,
            dc=dc,
            label=f"{spec['skill']} ({ability}) vs DC {dc}",
            forced_natural=player_d20_roll,
        )

        nat = roll_res["natural"]
        total = roll_res["total"]
        if roll_res["is_nat20"]:
            verdict = f"CRITICAL HIT / TRIUMPH (Nat 20! Total {total} vs DC {dc})"
            detail = f"Rolled a Natural 20 on {spec['skill']} ({ability} {total_mod:+d})! Automatic critical success with amplified effect."
        elif roll_res["is_nat1"]:
            verdict = f"CRITICAL FUMBLE (Nat 1! Total {total} vs DC {dc})"
            detail = f"Rolled a Natural 1 on {spec['skill']} ({ability} {total_mod:+d})! Automatic fumble — fate twists dangerously."
        elif roll_res["success"]:
            verdict = f"SUCCESS ({total} vs DC {dc})"
            detail = f"Rolled d20={nat} {total_mod:+d} = {total} against DC {dc} ({spec['skill']} / {ability}). Check succeeded!"
        else:
            verdict = f"FAILURE ({total} vs DC {dc})"
            detail = f"Rolled d20={nat} {total_mod:+d} = {total} against DC {dc} ({spec['skill']} / {ability}). Missed target DC by {dc - total}."

        return {
            "agent": cls.name,
            "check_kind": spec["check_kind"],
            "ability": ability,
            "skill": spec["skill"],
            "dc": dc,
            "modifier": total_mod,
            "roll": roll_res,
            "verdict": verdict,
            "summary": detail,
            "spec": spec,
        }


class NPCActorAgent:
    """Roleplays NPCs with voice quirks, secret motives, and persistent Disposition Meter."""

    name = "NPC Actor & Relationship Memory"

    @classmethod
    def interact(
        cls,
        campaign: dict[str, Any],
        action_text: str,
        rules_result: dict[str, Any],
        target_npc_id: str | None = None,
    ) -> dict[str, Any]:
        npcs = campaign.get("npcs", [])
        if not npcs:
            return {
                "agent": cls.name,
                "active": False,
                "summary": "No NPCs present in this chamber.",
            }

        txt = (action_text or "").lower()
        target_npc = None
        if target_npc_id:
            target_npc = next((n for n in npcs if n.get("id") == target_npc_id), None)
        if not target_npc:
            for n in npcs:
                if n["name"].lower().split()[0] in txt or n["id"].lower() in txt:
                    target_npc = n
                    break
        if not target_npc:
            # Pick nearest NPC to hero
            hx, hy = int(campaign["battlemap"]["hero_pos"]["x"]), int(campaign["battlemap"]["hero_pos"]["y"])
            target_npc = min(npcs, key=lambda n: math.hypot(int(n.get("x", 3)) - hx, int(n.get("y", 2)) - hy))

        old_disp = target_npc.get("disposition", "Neutral")
        old_score = int(target_npc.get("disposition_score", disposition_to_default_score(old_disp)))

        is_social = (
            target_npc_id is not None
            or rules_result.get("ability") == "CHA"
            or any(
                w in txt
                for w in (
                    "talk",
                    "speak",
                    "ask",
                    "greet",
                    "bribe",
                    "gold",
                    "promise",
                    "swear",
                    "threaten",
                    "intimidate",
                    "persuade",
                    "ally",
                    "help",
                    "secret",
                    target_npc["name"].lower().split()[0],
                )
            )
        )

        delta = 0
        reason = "Observed hero's actions in the chamber"
        hero = campaign["hero"]
        roll = rules_result["roll"]

        if is_social:
            if any(w in txt for w in ("bribe", "gold", "coin", "pay", "reward")):
                bribe_cost = min(25, int(hero.get("gold", 0)))
                if bribe_cost > 0:
                    hero["gold"] = int(hero.get("gold", 0)) - bribe_cost
                delta = 28 if roll["success"] else 14
                reason = f"Offered a {bribe_cost} gp bribe ('{action_text[:48]}')"
            elif any(w in txt for w in ("promise", "swear", "oath", "protect", "help", "ally", "friend", "peace", "aid")):
                delta = 26 if roll["success"] else 12
                reason = f"Swore a solemn promise/alliance ('{action_text[:48]}')"
            elif any(w in txt for w in ("threaten", "intimidate", "kill", "die", "surrender")):
                delta = -28 if not roll["success"] else -15
                reason = f"Issued a direct threat ('{action_text[:48]}')"
            else:
                delta = 18 if roll["success"] else -8
                reason = f"Parleyed with {target_npc['name']} ({rules_result['skill']})"

            if roll["is_nat20"]:
                delta += 18
            elif roll["is_nat1"]:
                delta -= 15

        new_score = max(-100, min(100, old_score + delta))
        new_disp = score_to_disposition(new_score)
        target_npc["disposition_score"] = new_score
        target_npc["disposition"] = new_disp

        # Record persistent relationship memory if social or disposition shifted
        memory_log = target_npc.setdefault("memory_log", [])
        if is_social or delta != 0:
            shift_str = f"{old_disp} → {new_disp}" if old_disp != new_disp else f"{new_disp} ({delta:+d})"
            memory_log.append(
                {
                    "time": time.strftime("%H:%M:%S"),
                    "event": reason,
                    "shift": shift_str,
                    "disposition": new_disp,
                }
            )
            if len(memory_log) > 12:
                del memory_log[:-12]

        # Build authentic dialogue using NPC's voice quirk & secret motive
        quirk = target_npc.get("voice_quirk", "Speaks in a measured, resonant cadence")
        motive = target_npc.get("secret_motive", "Seeks safe passage out of the dungeon.")
        secret_revealed = new_disp in ("Friendly", "Sworn Ally")
        target_npc["secret_revealed"] = secret_revealed

        if new_disp == "Sworn Ally":
            dialogue = (
                f"[{quirk}] \"By blood and starlight, {hero['name']}, you have my blade and my trust! "
                f"Hear my secret truth: {motive} Take my counsel—strike the sanctum guardian's flank!\""
            )
        elif new_disp == "Friendly":
            dialogue = (
                f"[{quirk}] \"You speak with rare honor, {hero['name']}. I will share what I guard: "
                f"{motive} Watch the floor plates ahead—they are rigged.\""
            )
        elif new_disp == "Neutral":
            dialogue = (
                f"[{quirk}] \"Words are cheap in the {campaign['battlemap']['biome_name']}, traveler. "
                f"Prove your worth or make a fair offer, and perhaps we can help each other.\""
            )
        elif new_disp == "Suspicious":
            dialogue = (
                f"[{quirk}] \"Keep your hands where I can see them, {hero['name']}. "
                f"One false move and this chamber becomes your tomb.\""
            )
        else:
            dialogue = (
                f"[{quirk}] \"Enough talk! Your arrogance ends here—steel and arcane fire will settle our debt!\""
            )

        return {
            "agent": cls.name,
            "active": True,
            "npc_id": target_npc["id"],
            "npc_name": target_npc["name"],
            "npc_title": target_npc.get("title", ""),
            "voice_quirk": quirk,
            "secret_motive": motive if secret_revealed else "🔒 Hidden until Friendly or Sworn Ally",
            "secret_revealed": secret_revealed,
            "old_disposition": old_disp,
            "new_disposition": new_disp,
            "disposition_score": new_score,
            "delta": delta,
            "dialogue": dialogue,
            "summary": f"{target_npc['name']} ({old_disp} → {new_disp}, score {new_score:+d}): {dialogue}",
        }


class TacticalDirectorAgent:
    """Manages turn-based initiative order, monster AI moves, HP/AC tracking, and loot drops."""

    name = "Tactical Encounter Director"

    @classmethod
    def sync_initiative(cls, campaign: dict[str, Any]) -> dict[str, Any]:
        combat = campaign.setdefault(
            "combat",
            {
                "active": True,
                "round": 1,
                "turn_index": 0,
                "order": [],
                "last_loot": [],
            },
        )
        hero = campaign["hero"]
        monsters = campaign.get("monsters", [])
        npcs = campaign.get("npcs", [])

        existing_init = {c["id"]: c["initiative"] for c in combat.get("order", [])}
        order: list[dict[str, Any]] = []

        hero_init = existing_init.get(hero["id"], 15 + int(hero.get("modifiers", {}).get("DEX", 2)))
        order.append(
            {
                "id": hero["id"],
                "name": hero["name"],
                "side": "hero",
                "portrait": hero.get("portrait", "/static/assets/portraits/hero_paladin.jpg"),
                "miniature": hero.get("miniature", "paladin"),
                "initiative": hero_init,
                "hp": hero["hp"],
                "max_hp": hero["max_hp"],
                "ac": hero["ac"],
                "alive": hero["hp"] > 0,
            }
        )

        for idx, mon in enumerate(monsters):
            m_init = existing_init.get(mon["id"], int(mon.get("initiative", 12 - idx * 2)))
            order.append(
                {
                    "id": mon["id"],
                    "name": mon["name"],
                    "side": "monster",
                    "portrait": mon.get("portrait", "/static/assets/portraits/monster_dragon.jpg"),
                    "miniature": mon.get("miniature", "dragon"),
                    "initiative": m_init,
                    "hp": mon["hp"],
                    "max_hp": mon["max_hp"],
                    "ac": mon["ac"],
                    "alive": mon["hp"] > 0,
                }
            )

        for npc in npcs:
            if npc.get("disposition") == "Sworn Ally":
                n_init = existing_init.get(npc["id"], 13)
                order.append(
                    {
                        "id": npc["id"],
                        "name": f"{npc['name']} (Ally)",
                        "side": "ally",
                        "portrait": npc.get("portrait", "/static/assets/portraits/hero_wizard.jpg"),
                        "miniature": npc.get("miniature", "wizard"),
                        "initiative": n_init,
                        "hp": 28,
                        "max_hp": 28,
                        "ac": 15,
                        "alive": True,
                    }
                )

        order.sort(key=lambda c: c["initiative"], reverse=True)
        combat["order"] = order
        combat["active"] = any(m["hp"] > 0 for m in monsters)
        if combat["order"]:
            combat["turn_index"] = int(combat.get("turn_index", 0)) % len(combat["order"])
        return combat

    @classmethod
    def resolve_combat_turn(
        cls,
        campaign: dict[str, Any],
        action_text: str,
        action_type: str,
        rules_result: dict[str, Any],
        target_monster_id: str | None = None,
    ) -> dict[str, Any]:
        combat = cls.sync_initiative(campaign)
        hero = campaign["hero"]
        monsters = campaign.get("monsters", [])
        living_monsters = [m for m in monsters if int(m.get("hp", 0)) > 0]

        hx, hy = int(campaign["battlemap"]["hero_pos"]["x"]), int(campaign["battlemap"]["hero_pos"]["y"])
        events: list[str] = []
        loot_dropped: list[dict[str, Any]] = []
        damage_dealt = 0
        damage_taken = 0

        # Identify target monster
        target_mon = None
        if target_monster_id:
            target_mon = next((m for m in living_monsters if m["id"] == target_monster_id), None)
        if not target_mon and living_monsters:
            txt = (action_text or "").lower()
            for m in living_monsters:
                if m["name"].lower().split()[0] in txt or m["id"].lower() in txt:
                    target_mon = m
                    break
            if not target_mon:
                target_mon = min(living_monsters, key=lambda m: tile_distance_ft(hx, hy, int(m["x"]), int(m["y"])))

        spec = rules_result.get("spec", {})
        roll = rules_result["roll"]
        is_offensive = spec.get("check_kind") in ("Attack Roll", "Spell Attack / Invocation")

        # Handle healing spells first
        if spec.get("heal_dice"):
            spell = spec.get("spell", {})
            cost = int(spell.get("cost_mana", 3))
            hero["mana"] = max(0, int(hero.get("mana", 10)) - cost)
            cnt, sds, mod = parse_dice_expr(spec["heal_dice"])
            heal_roll = roll_polyhedral(sides=sds, count=cnt, modifier=mod, label=f"Heal ({spell.get('name', 'Spell')})")
            healed = heal_roll["total"]
            old_hp = hero["hp"]
            hero["hp"] = min(hero["max_hp"], hero["hp"] + healed)
            events.append(f"{hero['name']} cast {spell.get('name', 'Healing Spell')} and restored +{hero['hp'] - old_hp} HP!")

        elif is_offensive and target_mon:
            spell = spec.get("spell")
            if spell:
                cost = int(spell.get("cost_mana", 2))
                hero["mana"] = max(0, int(hero.get("mana", 10)) - cost)

            if roll["success"]:
                dmg_expr = spec.get("damage_dice") or "1d8+3"
                cnt, sds, mod = parse_dice_expr(dmg_expr)
                if roll["is_nat20"]:
                    cnt *= 2  # Critical hit doubles damage dice!
                dmg_roll = roll_polyhedral(sides=sds, count=cnt, modifier=mod, label="Damage Roll")
                damage_dealt = max(1, dmg_roll["total"])
                target_mon["hp"] = max(0, int(target_mon["hp"]) - damage_dealt)
                crit_tag = "CRITICAL STRIKE! " if roll["is_nat20"] else ""
                events.append(
                    f"{crit_tag}{hero['name']} hit {target_mon['name']} for {damage_dealt} damage "
                    f"({dmg_roll['formula']})! [{target_mon['name']} HP: {target_mon['hp']}/{target_mon['max_hp']}]"
                )

                # Check if a Sworn Ally NPC assists!
                sworn_allies = [n for n in campaign.get("npcs", []) if n.get("disposition") == "Sworn Ally"]
                if sworn_allies and target_mon["hp"] > 0:
                    ally = sworn_allies[0]
                    ally_dmg = 5
                    target_mon["hp"] = max(0, target_mon["hp"] - ally_dmg)
                    events.append(f"Sworn Ally {ally['name']} flanked {target_mon['name']} for +{ally_dmg} bonus damage!")

                # Check monster defeat & loot drop
                if target_mon["hp"] <= 0:
                    xp_gain = int(target_mon.get("xp_reward", 450))
                    gold_gain = int(target_mon.get("gold_reward", 65))
                    hero["gold"] = int(hero.get("gold", 0)) + gold_gain
                    _, leveled, xp_msg = award_xp(hero, xp_gain)
                    loot_item = target_mon.get("loot_drop")
                    if loot_item:
                        hero.setdefault("inventory", []).append(dict(loot_item))
                        loot_dropped.append(loot_item)
                        combat.setdefault("last_loot", []).append(loot_item)
                    events.append(
                        f"🏆 DEFEATED {target_mon['name']}! Earned +{gold_gain} gp, {xp_msg}"
                        + (f" Looted [{loot_item['name']}]!" if loot_item else "")
                    )
            else:
                if roll["is_nat1"]:
                    hero["hp"] = max(1, int(hero["hp"]) - 2)
                    events.append(
                        f"Critical Fumble! {hero['name']}'s strike ricocheted off the stonework (-2 HP recoil) and missed {target_mon['name']}."
                    )
                else:
                    events.append(
                        f"{hero['name']}'s attack ({roll['total']}) glanced off {target_mon['name']}'s armor (AC {target_mon['ac']})."
                    )

        # Monster AI Counter-Turn if any living monster is within 30 ft (6 tiles) or was attacked
        living_monsters = [m for m in monsters if int(m.get("hp", 0)) > 0]
        if living_monsters:
            nearest_mon = min(living_monsters, key=lambda m: tile_distance_ft(hx, hy, int(m["x"]), int(m["y"])))
            dist_ft = tile_distance_ft(hx, hy, int(nearest_mon["x"]), int(nearest_mon["y"]))

            if is_offensive or dist_ft <= 25:
                # Move monster 1 step closer if > 5 ft away
                if dist_ft > 5:
                    path = shortest_walkable_path(
                        campaign["battlemap"],
                        (int(nearest_mon["x"]), int(nearest_mon["y"])),
                        (hx, hy),
                        max_steps=2,
                    )
                    if path and path[0] != (hx, hy):
                        nearest_mon["x"], nearest_mon["y"] = path[0]
                        dist_ft = tile_distance_ft(hx, hy, int(nearest_mon["x"]), int(nearest_mon["y"]))

                if dist_ft <= int(nearest_mon.get("range_ft", 25)):
                    m_atk_roll = roll_polyhedral(
                        sides=20,
                        count=1,
                        modifier=int(nearest_mon.get("attack_bonus", 4)),
                        dc=int(hero["ac"]),
                        label=f"{nearest_mon['name']} Attack vs Hero AC {hero['ac']}",
                    )
                    if m_atk_roll["success"]:
                        m_dmg = max(2, int(nearest_mon.get("damage", 5)) + (3 if m_atk_roll["is_nat20"] else 0))
                        hero["hp"] = max(1, int(hero["hp"]) - m_dmg)
                        damage_taken = m_dmg
                        events.append(
                            f"⚠️ {nearest_mon['name']} used {nearest_mon.get('attack_name', 'Rend')} "
                            f"(rolled {m_atk_roll['total']} vs AC {hero['ac']}) and dealt {m_dmg} damage! "
                            f"[Hero HP: {hero['hp']}/{hero['max_hp']}]"
                        )
                    else:
                        events.append(
                            f"🛡️ {nearest_mon['name']} lunged with {nearest_mon.get('attack_name', 'Strike')} "
                            f"(rolled {m_atk_roll['total']} vs AC {hero['ac']}), but {hero['name']} parried!"
                        )

        combat["round"] = int(combat.get("round", 1)) + (1 if is_offensive else 0)
        cls.sync_initiative(campaign)
        recalc_hero(hero)

        if not events:
            if living_monsters:
                nearest = min(living_monsters, key=lambda m: tile_distance_ft(hx, hy, int(m["x"]), int(m["y"])))
                d_ft = tile_distance_ft(hx, hy, int(nearest["x"]), int(nearest["y"]))
                events.append(
                    f"Tactical radar: {nearest['name']} (HP {nearest['hp']}/{nearest['max_hp']}, AC {nearest['ac']}) is {d_ft} ft away."
                )
            else:
                events.append("All hostile threats in this sector have been neutralized.")

        return {
            "agent": cls.name,
            "round": combat["round"],
            "active_combat": combat["active"],
            "initiative_order": combat["order"],
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
            "loot_dropped": loot_dropped,
            "events": events,
            "summary": " ".join(events),
        }


class WorldbuilderGMAgent:
    """Synthesizes atmospheric scene description, sensory details, and all 3 sibling agents' outputs."""

    name = "Worldbuilder & Narrative GM"

    SENSORY_PALETTES: dict[str, list[str]] = {
        "sunken_obsidian_crypt": [
            "Violet soul-flames gutter in carved basalt sconces while ancient dust drifts from the vaulted ceiling.",
            "The air tastes of cold iron and ozone as whispered prayers echo off obsidian sarcophagi.",
            "Faint amethyst ley-lines pulse beneath the cracked flagstones in rhythm with your heartbeat.",
        ],
        "dragons_ember_cavern": [
            "Rivers of incandescent magma cast dancing crimson reflections across the jagged obsidian pillars.",
            "Sulfurous heat shimmers over the basalt causeway while embers spiral toward the cavern roof.",
            "The low tectonic rumble of the caldera vibrates through the soles of your boots.",
        ],
        "clockwork_astral_spire": [
            "Colossal brass escapement gears interlock overhead, ticking in harmonic resonance with the stars.",
            "Arcs of cerulean starlight hum through crystal conduits embedded in the polished floor.",
            "The scent of hot copper and ozone fills the observatory as pendulums swing through zero-gravity rifts.",
        ],
        "whispering_feywild_grove": [
            "Bioluminescent spore-lanterns drift between silver willow roots, bathing the glade in emerald twilight.",
            "Crystalline rime-frost crackles underfoot while distant sylvan chimes ring through the mist.",
            "Ancient heartwood trees lean inward as if listening to every word spoken in the clearing.",
        ],
        "rustport_tavern_brawl": [
            "Wrought-iron chandeliers sway above lantern-lit oak tables slick with spiced Kraken rum.",
            "Rain lashes the salt-frosted port windows while sea-shanties and clashing steel echo from the cellar.",
            "Hearth-smoke and roasting sea-pepper mingle with the sharp tang of blackpowder and bilge-water.",
        ],
        "starship_derelict_deck": [
            "Emergency holo-strobes bathe the titanium bulkheads in pulsing cyan light as cryo-mist vents across the deck.",
            "Ruptured plasma conduits hiss behind reinforced durasteel grating while artificial gravity hums.",
            "Starfields wheel silently beyond the armored viewport of the derelict dreadnought.",
        ],
    }

    @classmethod
    def narrate(
        cls,
        campaign: dict[str, Any],
        action_text: str,
        rules_res: dict[str, Any],
        npc_res: dict[str, Any],
        tactical_res: dict[str, Any],
        settings: DMOSSettings | None = None,
    ) -> dict[str, Any]:
        cfg = settings or load_settings()
        bmap = campaign["battlemap"]
        biome_id = bmap.get("biome_id", "sunken_obsidian_crypt")
        room_name = current_room_name(bmap)
        hx, hy = int(bmap["hero_pos"]["x"]), int(bmap["hero_pos"]["y"])
        palettes = cls.SENSORY_PALETTES.get(biome_id, cls.SENSORY_PALETTES["sunken_obsidian_crypt"])
        sensory = palettes[(len(campaign.get("chronicle", [])) + hx + hy) % len(palettes)]

        roll = rules_res["roll"]
        hero = campaign["hero"]

        if roll["is_nat20"]:
            lead = (
                f"🌟 **CRITICAL TRIUMPH IN {room_name.upper()}!** {sensory} "
                f"With a legendary **Natural 20** (`{roll['total']}` vs `DC {rules_res['dc']}` on *{rules_res['skill']}*), "
                f"**{hero['name']}** executes `{action_text}` with breathtaking mastery!"
            )
        elif roll["is_nat1"]:
            lead = (
                f"💀 **CRITICAL FUMBLE IN {room_name.upper()}!** {sensory} "
                f"Fatebetrays **{hero['name']}** on a **Natural 1** (`{roll['total']}` vs `DC {rules_res['dc']}` on *{rules_res['skill']}*) "
                f"while attempting `{action_text}`—sparks and peril erupt across the flagstones!"
            )
        elif roll["success"]:
            lead = (
                f"✨ **{room_name}** — {sensory} "
                f"Drawing upon **{rules_res['ability']}** (`{roll['total']}` vs `DC {rules_res['dc']}` on *{rules_res['skill']}*), "
                f"**{hero['name']}** succeeds: *{action_text}*."
            )
        else:
            lead = (
                f"⚡ **{room_name}** — {sensory} "
                f"**{hero['name']}** attempts *{action_text}*, testing **{rules_res['ability']}** (`{roll['total']}` vs `DC {rules_res['dc']}`), "
                f"but the dungeon's resistance holds firm."
            )

        parts = [lead]
        if tactical_res.get("events"):
            parts.append("**Tactical Resolution:** " + " ".join(tactical_res["events"]))
        if npc_res.get("active") and npc_res.get("dialogue"):
            parts.append(f"**{npc_res['npc_name']} ({npc_res['new_disposition']}):** {npc_res['dialogue']}")

        narrative_md = "\n\n".join(parts)

        # Optional Local Ollama / Cloud LLM enrichment when configured
        provider = cfg.effective_provider()
        llm_used = "offline"
        if provider in ("ollama", "openai", "anthropic"):
            enriched = cls._try_llm_enrich(cfg, provider, campaign, action_text, narrative_md)
            if enriched:
                narrative_md = enriched
                llm_used = provider

        suggestions = cls.suggest_actions(campaign)
        return {
            "agent": cls.name,
            "provider": llm_used,
            "room_name": room_name,
            "narrative": narrative_md,
            "summary": lead,
            "suggested_actions": suggestions,
        }

    @classmethod
    def suggest_actions(cls, campaign: dict[str, Any]) -> list[dict[str, str]]:
        hero = campaign["hero"]
        living_monsters = [m for m in campaign.get("monsters", []) if int(m.get("hp", 0)) > 0]
        npcs = campaign.get("npcs", [])
        spells = hero.get("spells", [])
        first_spell = spells[0]["name"] if spells else "Arcane Bolt"

        suggestions: list[dict[str, str]] = []
        if living_monsters:
            m = living_monsters[0]
            suggestions.append({"label": f"⚔️ Strike {m['name']}", "action": f"Attack {m['name']} with equipped weapon", "type": "attack"})
            suggestions.append({"label": f"✨ Cast {first_spell}", "action": f"Cast {first_spell} at {m['name']}", "type": "spell"})
        if npcs:
            n = npcs[0]
            suggestions.append({"label": f"🤝 Parley / Promise {n['name'].split()[0]}", "action": f"Swear an honorable promise to help {n['name']} and ask for their secret", "type": "roleplay"})
            suggestions.append({"label": f"🪙 Bribe {n['name'].split()[0]} (25 gp)", "action": f"Offer gold coin to bribe {n['name']} into becoming our ally", "type": "roleplay"})
        suggestions.append({"label": "🔍 Inspect Chamber & Traps", "action": "Search the chamber flagstones for hidden traps, runes, and secret switches", "type": "explore"})
        return suggestions[:4]

    @classmethod
    def _try_llm_enrich(
        cls,
        cfg: DMOSSettings,
        provider: str,
        campaign: dict[str, Any],
        action_text: str,
        fallback_narrative: str,
    ) -> str | None:
        prompt = (
            f"You are the Worldbuilder & Narrative GM of Dungeon Master OS in the '{campaign['battlemap']['biome_name']}'.\n"
            f"Hero: {campaign['hero']['name']} ({campaign['hero']['class_name']}).\n"
            f"Player Action: {action_text}\n"
            f"Mechanical & NPC Outcome:\n{fallback_narrative}\n\n"
            "Write a vivid, atmospheric 2-paragraph tabletop RPG narration incorporating these exact mechanical results and NPC dialogue."
        )
        try:
            if provider == "ollama":
                r = httpx.post(
                    f"{cfg.ollama_url.rstrip('/')}/api/chat",
                    json={
                        "model": cfg.ollama_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                    timeout=3.5,
                )
                if r.status_code == 200:
                    content = r.json().get("message", {}).get("content", "").strip()
                    if content:
                        return content + "\n\n---\n" + fallback_narrative
        except Exception:
            pass
        return None


def run_gm_turn(
    campaign: dict[str, Any],
    action_text: str,
    action_type: str = "roleplay",
    dice_mode: DiceMode = "normal",
    player_d20_roll: int | None = None,
    target_npc_id: str | None = None,
    target_monster_id: str | None = None,
) -> dict[str, Any]:
    """Execute the full 4-Agent Tabletop GM pipeline for a player action and append to the campaign chronicle."""
    hero = campaign["hero"]
    npcs = campaign.get("npcs", [])
    monsters = [m for m in campaign.get("monsters", []) if int(m.get("hp", 0)) > 0]

    target_npc = next((n for n in npcs if n["id"] == target_npc_id), (npcs[0] if npcs else None))
    target_mon = next((m for m in monsters if m["id"] == target_monster_id), (monsters[0] if monsters else None))

    # 1. Rules Lawyer & D20 Mechanics Agent
    rules_res = RulesLawyerAgent.evaluate(
        action_text=action_text,
        action_type=action_type,
        hero=hero,
        target_npc=target_npc,
        target_monster=target_mon,
        dice_mode=dice_mode,
        player_d20_roll=player_d20_roll,
    )

    # Record the d20 roll in the campaign dice history
    campaign.setdefault("dice_history", []).insert(0, rules_res["roll"])
    del campaign["dice_history"][40:]

    # 2. NPC Actor Agent with Persistent Relationship Memory
    npc_res = NPCActorAgent.interact(
        campaign=campaign,
        action_text=action_text,
        rules_result=rules_res,
        target_npc_id=target_npc_id,
    )

    # 3. Tactical Encounter Director
    tactical_res = TacticalDirectorAgent.resolve_combat_turn(
        campaign=campaign,
        action_text=action_text,
        action_type=action_type,
        rules_result=rules_res,
        target_monster_id=target_monster_id,
    )

    # 4. Worldbuilder & Narrative GM Agent
    world_res = WorldbuilderGMAgent.narrate(
        campaign=campaign,
        action_text=action_text,
        rules_res=rules_res,
        npc_res=npc_res,
        tactical_res=tactical_res,
    )

    entry = {
        "id": f"turn_{int(time.time() * 1000)}_{random.randint(100, 999)}",
        "timestamp": time.strftime("%H:%M:%S"),
        "player_action": action_text,
        "action_type": action_type,
        "room_name": world_res["room_name"],
        "narrative": world_res["narrative"],
        "agents": {
            "worldbuilder": {
                "name": world_res["agent"],
                "summary": world_res["summary"],
                "provider": world_res["provider"],
            },
            "rules_lawyer": {
                "name": rules_res["agent"],
                "verdict": rules_res["verdict"],
                "summary": rules_res["summary"],
                "ability": rules_res["ability"],
                "skill": rules_res["skill"],
                "dc": rules_res["dc"],
                "roll": rules_res["roll"],
            },
            "npc_actor": {
                "name": npc_res["agent"],
                "npc_name": npc_res.get("npc_name"),
                "disposition": npc_res.get("new_disposition"),
                "delta": npc_res.get("delta", 0),
                "dialogue": npc_res.get("dialogue", ""),
                "summary": npc_res["summary"],
            },
            "tactical_director": {
                "name": tactical_res["agent"],
                "round": tactical_res["round"],
                "damage_dealt": tactical_res["damage_dealt"],
                "damage_taken": tactical_res["damage_taken"],
                "loot_dropped": tactical_res["loot_dropped"],
                "summary": tactical_res["summary"],
            },
        },
    }

    campaign.setdefault("chronicle", []).append(entry)
    campaign["suggested_actions"] = world_res["suggested_actions"]
    campaign["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return entry


def move_hero_token(
    campaign: dict[str, Any],
    target_x: int,
    target_y: int,
) -> dict[str, Any]:
    """Move hero token along walkable path to (target_x, target_y), reveal Fog of War, and trigger tile encounters."""
    bmap = campaign["battlemap"]
    hero = campaign["hero"]
    hx, hy = int(bmap["hero_pos"]["x"]), int(bmap["hero_pos"]["y"])
    width, height = int(bmap["width"]), int(bmap["height"])

    if not (0 <= target_x < width and 0 <= target_y < height):
        raise ValueError("Target coordinates are outside the battlemap grid.")

    dest_cell = bmap["tiles"][target_y][target_x]
    if dest_cell["kind"] in ("wall", "pillar"):
        raise ValueError("Cannot move onto a solid wall or pillar tile.")

    path = shortest_walkable_path(bmap, (hx, hy), (target_x, target_y), max_steps=10)
    if not path and (hx, hy) != (target_x, target_y):
        # Allow direct step if adjacent
        if abs(target_x - hx) <= 1 and abs(target_y - hy) <= 1:
            path = [(target_x, target_y)]
        else:
            raise ValueError("No walkable path to that tile.")

    triggered_events: list[str] = []
    distance_moved_ft = 0
    curr_x, curr_y = hx, hy

    for nx, ny in path:
        step_ft = tile_distance_ft(curr_x, curr_y, nx, ny)
        distance_moved_ft += step_ft
        curr_x, curr_y = nx, ny
        bmap["hero_pos"] = {"x": curr_x, "y": curr_y}
        update_fog_of_war(bmap, vision_radius=int(hero.get("vision_radius", 5)))

        cell = bmap["tiles"][curr_y][curr_x]

        # 1. Auto-open closed doors
        if cell["kind"] == "door" and not cell.get("opened"):
            cell["opened"] = True
            update_fog_of_war(bmap, vision_radius=int(hero.get("vision_radius", 5)))
            triggered_events.append(f"🚪 Unbarred and pushed open the heavy dungeon door at ({curr_x}, {curr_y}), revealing the chamber beyond!")

        # 2. Open Treasure Chests
        chest = cell.get("chest")
        if chest and not chest.get("opened"):
            chest["opened"] = True
            gold_found = int(chest.get("gold", 50))
            item = chest.get("item")
            hero["gold"] = int(hero.get("gold", 0)) + gold_found
            if item:
                hero.setdefault("inventory", []).append(dict(item))
            _, _, xp_msg = award_xp(hero, 150)
            triggered_events.append(
                f"🧰 Opened **{chest['name']}** at ({curr_x}, {curr_y})! Found **+{gold_found} gp**"
                + (f" and **[{item['name']}]**!" if item else "!")
                + f" ({xp_msg})"
            )

        # 3. Trigger Traps with automatic Saving Throw
        trap = cell.get("trap")
        if trap and not trap.get("triggered") and not trap.get("disarmed"):
            trap["triggered"] = True
            ab = trap.get("ability", "DEX")
            mod = int(hero.get("modifiers", {}).get(ab, 0)) + int(hero.get("proficiency_bonus", 2))
            save_roll = roll_polyhedral(
                sides=20,
                count=1,
                modifier=mod,
                dc=int(trap.get("dc", 13)),
                label=f"{ab} Saving Throw vs {trap['name']}",
            )
            campaign.setdefault("dice_history", []).insert(0, save_roll)
            if save_roll["success"]:
                triggered_events.append(
                    f"⚡ Triggered **{trap['name']}** at ({curr_x}, {curr_y}), but {hero['name']} passed the "
                    f"**{ab} Save** (`{save_roll['total']}` vs `DC {trap['dc']}`) and evaded all damage!"
                )
            else:
                dmg = int(trap.get("damage", 5))
                hero["hp"] = max(1, int(hero["hp"]) - dmg)
                triggered_events.append(
                    f"💥 Sprung **{trap['name']}** at ({curr_x}, {curr_y})! Failed **{ab} Save** "
                    f"(`{save_roll['total']}` vs `DC {trap['dc']}`) and suffered **-{dmg} HP**!"
                )

        # 4. Environmental Hazards (Lava, Ice, Arcane Rune)
        hazard = cell.get("hazard")
        if hazard:
            htype = hazard.get("type")
            if htype == "arcane_rune":
                mana_gain = int(hazard.get("buff_mana", 3))
                hero["mana"] = min(int(hero["max_mana"]), int(hero["mana"]) + mana_gain)
                triggered_events.append(f"🔮 Stepped onto **{hazard['name']}** at ({curr_x}, {curr_y}): absorbed **+{mana_gain} Mana**!")
            elif htype == "lava":
                dmg = int(hazard.get("damage", 4))
                hero["hp"] = max(1, int(hero["hp"]) - dmg)
                triggered_events.append(f"🔥 Crossed **{hazard['name']}** at ({curr_x}, {curr_y}): seared for **-{dmg} HP**!")
            elif htype == "ice":
                triggered_events.append(f"❄️ Crossed **{hazard['name']}** at ({curr_x}, {curr_y}): footing is slick (`5 ft` difficult terrain).")

        # 5. Sanctum Exit Portal
        if cell["kind"] == "exit":
            triggered_events.append(
                f"🌀 Reached the **Sanctum Astral Waygate** at ({curr_x}, {curr_y})! You can transition this campaign to a new biome or claim victory."
            )

    recalc_hero(hero)
    room_name = current_room_name(bmap)

    # Check proximity to NPCs and Monsters
    for npc in campaign.get("npcs", []):
        d_ft = tile_distance_ft(curr_x, curr_y, int(npc["x"]), int(npc["y"]))
        if d_ft <= 10:
            triggered_events.append(
                f"💬 Within `{d_ft} ft` of **{npc['name']}** (*{npc['disposition']}*): \"{npc.get('greeting', 'State your business, traveler.')}\""
            )

    for mon in campaign.get("monsters", []):
        if int(mon.get("hp", 0)) > 0:
            d_ft = tile_distance_ft(curr_x, curr_y, int(mon["x"]), int(mon["y"]))
            if d_ft <= 15:
                triggered_events.append(
                    f"⚔️ Hostile **{mon['name']}** (`HP {mon['hp']}/{mon['max_hp']}`, `AC {mon['ac']}`) is `{d_ft} ft` away!"
                )

    if triggered_events:
        entry = {
            "id": f"move_{int(time.time() * 1000)}_{random.randint(100, 999)}",
            "timestamp": time.strftime("%H:%M:%S"),
            "player_action": f"Move {distance_moved_ft} ft to ({curr_x}, {curr_y}) in {room_name}",
            "action_type": "move",
            "room_name": room_name,
            "narrative": f"🥾 **{hero['name']}** moved `{distance_moved_ft} ft` to `({curr_x}, {curr_y})` in **{room_name}**.\n\n"
            + "\n".join(f"- {ev}" for ev in triggered_events),
            "agents": {
                "worldbuilder": {"name": WorldbuilderGMAgent.name, "summary": f"Revealed {len(bmap['visible'])} tiles in {room_name}.", "provider": "offline"},
                "rules_lawyer": {"name": RulesLawyerAgent.name, "verdict": f"Range {distance_moved_ft} ft ({len(path)} tiles)", "summary": "Measured movement at 5 ft/tile."},
                "npc_actor": {"name": NPCActorAgent.name, "summary": "Tracked proximity to scene NPCs."},
                "tactical_director": {"name": TacticalDirectorAgent.name, "summary": f"Updated token coordinates to ({curr_x}, {curr_y})."},
            },
        }
        campaign.setdefault("chronicle", []).append(entry)

    campaign["suggested_actions"] = WorldbuilderGMAgent.suggest_actions(campaign)
    campaign["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return {
        "hero_pos": bmap["hero_pos"],
        "distance_ft": distance_moved_ft,
        "room_name": room_name,
        "revealed_count": len(bmap["revealed"]),
        "visible_count": len(bmap["visible"]),
        "events": triggered_events,
    }
