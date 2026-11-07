"""API smoke tests for Dungeon Master OS using FastAPI TestClient."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dungeon_master_os.server import app


def test_api_end_to_end_smoke() -> None:
    with TestClient(app) as client:
        # 1. Health check
        r = client.get("/api/health")
        assert r.status_code == 200
        h = r.json()
        assert h["status"] == "ok"
        assert h["biomes_count"] == 6
        assert h["heroes_count"] == 4
        assert h["campaigns_count"] >= 3

        # 2. Catalog
        cat = client.get("/api/catalog").json()
        assert len(cat["biomes"]) == 6
        assert len(cat["heroes"]) == 4
        assert cat["supported_dice"] == [4, 6, 8, 10, 12, 20, 100]

        # 3. Pre-loaded campaigns
        camps = client.get("/api/campaigns").json()["campaigns"]
        assert len(camps) >= 3
        cid = "camp_sunken_crypt"

        # 4. Load campaign
        c_res = client.get(f"/api/campaigns/{cid}")
        assert c_res.status_code == 200
        camp = c_res.json()["campaign"]
        assert camp["id"] == cid

        # 5. Token movement & Fog of War
        m_res = client.post(f"/api/campaigns/{cid}/move", json={"x": 3, "y": 3})
        assert m_res.status_code == 200
        assert m_res.json()["move"]["hero_pos"] == {"x": 3, "y": 3}

        f_res = client.post(f"/api/campaigns/{cid}/fog", json={"reveal_all": True})
        assert f_res.status_code == 200
        assert len(f_res.json()["campaign"]["battlemap"]["revealed"]) == 16 * 12

        # 6. 4-Agent GM Action
        a_res = client.post(
            f"/api/campaigns/{cid}/action",
            json={
                "action_text": "Parley with Vaelen and offer a 25 gp bribe",
                "action_type": "roleplay",
                "dice_mode": "adv",
                "player_d20_roll": 18,
            },
        )
        assert a_res.status_code == 200
        turn = a_res.json()["turn"]
        assert "worldbuilder" in turn["agents"]
        assert "rules_lawyer" in turn["agents"]
        assert "npc_actor" in turn["agents"]
        assert "tactical_director" in turn["agents"]

        # 7. Polyhedral Dice Roller & Stats
        for sides in (4, 6, 8, 10, 12, 20, 100):
            d_res = client.post(
                "/api/dice/roll",
                json={"sides": sides, "count": 1, "modifier": 3, "mode": "normal", "dc": 12, "campaign_id": cid},
            )
            assert d_res.status_code == 200
            assert d_res.json()["roll"]["sides"] == sides

        s_res = client.get("/api/dice/stats?sides=20&count=1&modifier=4&mode=adv&dc=15")
        assert s_res.status_code == 200
        assert "pass_probability_pct" in s_res.json()["stats"]

        # 8. Hero Item, Rest, XP, and Customize
        it_res = client.post(f"/api/campaigns/{cid}/hero/item", json={"item_id": "potion_healing"})
        assert it_res.status_code == 200

        pr_res = client.post(f"/api/campaigns/{cid}/hero/progress", json={"action": "xp", "xp_amount": 600})
        assert pr_res.status_code == 200

        cu_res = client.post(
            f"/api/campaigns/{cid}/hero/customize",
            json={"name": "Kaelen the Redeemed", "abilities": {"STR": 19}},
        )
        assert cu_res.status_code == 200
        assert cu_res.json()["campaign"]["hero"]["name"] == "Kaelen the Redeemed"

        # 9. Biome transition
        b_res = client.post(f"/api/campaigns/{cid}/biome", json={"biome_id": "dragons_ember_cavern"})
        assert b_res.status_code == 200
        assert b_res.json()["campaign"]["battlemap"]["biome_id"] == "dragons_ember_cavern"

        # 10. Exports (Markdown, HTML, PNG)
        md_res = client.get(f"/api/campaigns/{cid}/export.md")
        assert md_res.status_code == 200
        assert "Adventure Chronicle" in md_res.text

        html_res = client.get(f"/api/campaigns/{cid}/export.html")
        assert html_res.status_code == 200
        assert "<!DOCTYPE html>" in html_res.text

        png_res = client.get(f"/api/campaigns/{cid}/battlemap.png")
        assert png_res.status_code == 200
        assert png_res.content.startswith(b"\x89PNG")
