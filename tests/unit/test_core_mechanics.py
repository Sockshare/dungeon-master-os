"""Unit tests for Dungeon Master OS core mechanics: dice, heroes, 6 biomes, Fog of War, and 4-Agent GM."""

from __future__ import annotations

from dungeon_master_os.agents import (
    DISPOSITION_TIERS,
    move_hero_token,
    run_gm_turn,
    score_to_disposition,
)
from dungeon_master_os.battlemap import (
    BIOME_CATALOG,
    generate_battlemap,
    list_biomes,
    render_battlemap_png,
    tile_distance_ft,
)
from dungeon_master_os.campaigns import (
    create_campaign,
    ensure_showcase_campaigns,
    export_chronicle_html,
    export_chronicle_markdown,
)
from dungeon_master_os.dice import (
    SUPPORTED_DICE,
    dc_pass_probability,
    distribution_stats,
    parse_dice_expr,
    roll_polyhedral,
)
from dungeon_master_os.heroes import (
    HERO_PRESETS,
    ability_mod,
    award_xp,
    build_hero,
    equip_Or_use_item,
    list_hero_presets,
)


def test_polyhedral_dice_and_probabilities() -> None:
    assert SUPPORTED_DICE == (4, 6, 8, 10, 12, 20, 100)
    assert parse_dice_expr("2d8+4") == (2, 8, 4)
    assert parse_dice_expr("d20-1") == (1, 20, -1)

    for sides in SUPPORTED_DICE:
        res = roll_polyhedral(sides=sides, count=1, modifier=2, mode="normal", dc=10)
        assert res["sides"] == sides
        assert 1 <= res["natural"] <= sides
        assert res["total"] == res["natural"] + 2

    # Advantage vs Disadvantage roll structure
    adv_roll = roll_polyhedral(sides=20, count=1, modifier=3, mode="adv", dc=12)
    assert len(adv_roll["rolls"]) == 1 and len(adv_roll["discarded"]) == 1
    assert adv_roll["rolls"][0] >= adv_roll["discarded"][0]

    dis_roll = roll_polyhedral(sides=20, count=1, modifier=3, mode="dis", dc=12)
    assert dis_roll["rolls"][0] <= dis_roll["discarded"][0]

    # Critical Hit (Nat 20) & Critical Fumble (Nat 1)
    crit = roll_polyhedral(sides=20, modifier=0, dc=25, forced_natural=20)
    assert crit["is_nat20"] is True
    assert crit["success"] is True
    assert crit["outcome_tier"] == "critical_success"

    fumble = roll_polyhedral(sides=20, modifier=15, dc=10, forced_natural=1)
    assert fumble["is_nat1"] is True
    assert fumble["success"] is False
    assert fumble["outcome_tier"] == "critical_fumble"

    # Probability math
    p_norm = dc_pass_probability(20, 0, 11, "normal")
    p_adv = dc_pass_probability(20, 0, 11, "adv")
    p_dis = dc_pass_probability(20, 0, 11, "dis")
    assert abs(p_norm - 0.50) < 1e-4
    assert abs(p_adv - 0.75) < 1e-4
    assert abs(p_dis - 0.25) < 1e-4

    stats = distribution_stats(sides=20, count=1, modifier=4, mode="adv", dc=14)
    assert stats["crit_chance_pct"] == 9.75
    assert len(stats["histogram"]) == 20


def test_heroes_inventory_and_xp_leveling() -> None:
    presets = list_hero_presets()
    assert len(presets) == 4
    expected_ids = {"eldrin_chronomancer", "kaelen_paladin", "vex_rogue", "bram_artificer"}
    assert {h["id"] for h in presets} == expected_ids
    assert ability_mod(18) == 4
    assert ability_mod(10) == 0
    assert ability_mod(9) == -1

    hero = build_hero("kaelen_paladin")
    hero["hp"] = 15
    hero, msg = equip_Or_use_item(hero, "potion_healing")
    assert hero["hp"] > 15
    assert "Drank" in msg

    initial_ac = hero["ac"]
    hero, _ = equip_Or_use_item(hero, "obsidian_plate")
    assert hero["ac"] < initial_ac

    hero, leveled, xp_msg = award_xp(hero, 2000)
    assert leveled is True
    assert hero["level"] >= 4
    assert "LEVEL UP" in xp_msg


def test_six_biomes_fog_of_war_and_movement() -> None:
    biomes = list_biomes()
    assert len(biomes) == 6
    for b_id in BIOME_CATALOG:
        bmap = generate_battlemap(biome_id=b_id)
        assert bmap["width"] == 16 and bmap["height"] == 12
        assert bmap["tile_scale_ft"] == 5
        assert len(bmap["rooms"]) == 4
        assert len(bmap["revealed"]) > 0

    assert tile_distance_ft(2, 3, 5, 7) == 25  # 3-4-5 right triangle * 5 ft = 25 ft

    camp = create_campaign("Test Crypt", biome_id="sunken_obsidian_crypt", hero_preset_id="vex_rogue")
    initial_rev = len(camp["battlemap"]["revealed"])
    move_res = move_hero_token(camp, 5, 1)  # Move to chest in room 1
    assert move_res["hero_pos"] == {"x": 5, "y": 1}
    assert move_res["distance_ft"] > 0
    assert len(camp["battlemap"]["revealed"]) >= initial_rev
    assert any("Chest" in ev for ev in move_res["events"])

    png = render_battlemap_png(camp)
    assert png.startswith(b"\x89PNG")
    assert len(png) > 1500


def test_four_agent_gm_and_npc_disposition_memory() -> None:
    assert DISPOSITION_TIERS == ("Hostile", "Suspicious", "Neutral", "Friendly", "Sworn Ally")
    assert score_to_disposition(-60) == "Hostile"
    assert score_to_disposition(-20) == "Suspicious"
    assert score_to_disposition(0) == "Neutral"
    assert score_to_disposition(40) == "Friendly"
    assert score_to_disposition(80) == "Sworn Ally"

    camp = create_campaign("Crypt Test", biome_id="sunken_obsidian_crypt", hero_preset_id="kaelen_paladin")
    vaelen = camp["npcs"][0]
    assert vaelen["disposition"] == "Suspicious"

    # Bribe + Promise with Nat 20 shifts disposition upward and records persistent memory
    turn1 = run_gm_turn(
        camp,
        action_text="Offer 25 gold coin bribe and swear an oath to Vaelen",
        action_type="roleplay",
        player_d20_roll=20,
        target_npc_id=vaelen["id"],
    )
    assert turn1["agents"]["rules_lawyer"]["roll"]["is_nat20"] is True
    assert vaelen["disposition"] in ("Neutral", "Friendly", "Sworn Ally")
    assert len(vaelen["memory_log"]) >= 2

    # Second promise shifts Vaelen to Friendly or Sworn Ally and unlocks secret motive
    run_gm_turn(
        camp,
        action_text="Promise to protect the Silent Legion and help Vaelen",
        action_type="roleplay",
        player_d20_roll=19,
        target_npc_id=vaelen["id"],
    )
    assert vaelen["disposition"] in ("Friendly", "Sworn Ally")
    assert vaelen.get("secret_revealed") is True

    # Combat turn against monster
    mon = camp["monsters"][0]
    initial_m_hp = mon["hp"]
    turn_atk = run_gm_turn(
        camp,
        action_text=f"Attack {mon['name']} with Soulrender Greatsword",
        action_type="attack",
        player_d20_roll=20,
        target_monster_id=mon["id"],
    )
    assert mon["hp"] < initial_m_hp
    assert turn_atk["agents"]["tactical_director"]["damage_dealt"] > 0

    # Export Markdown & HTML
    shorts = ensure_showcase_campaigns()
    assert len(shorts) >= 3
    md = export_chronicle_markdown(camp)
    html_doc = export_chronicle_html(camp)
    assert "Adventure Chronicle" in md
    assert "<!DOCTYPE html>" in html_doc
