/* ============================================================================
 * Dungeon Master OS — 60FPS Painted Isometric 3D D&D Battlemap & Miniature Engine
 * Renders Ultra-Detailed 16:9 Hand-Painted Isometric Dungeons & Dragons Boards,
 * 16x12 Isometric Diamond Tactical Grid, Dynamic Brazier/Portal/Lava Lighting,
 * Sculpted 3D Portrait Miniature Standees, Camera Presets & Animated Spell VFX.
 * Works 100% Identically With or Without WebGL!
 * ============================================================================ */

(function () {
  "use strict";

  const TILE_SIZE = 2.0;

  const BOARD_ASSETS = {
    sunken_obsidian_crypt: "/static/assets/boards/board_sunken_crypt.jpg",
    whispering_feywild_grove: "/static/assets/boards/board_sunken_crypt.jpg",
    clockwork_astral_spire: "/static/assets/boards/board_sky_galleon.jpg",
    rustport_tavern_brawl: "/static/assets/boards/board_sky_galleon.jpg",
    starship_derelict_deck: "/static/assets/boards/board_sky_galleon.jpg",
    dragons_ember_cavern: "/static/assets/boards/board_dragon_lair.jpg",
  };

  const PORTRAIT_ASSETS = [
    "/static/assets/portraits/hero_paladin.jpg",
    "/static/assets/portraits/hero_wizard.jpg",
    "/static/assets/portraits/hero_rogue.jpg",
    "/static/assets/portraits/hero_sorcerer.jpg",
    "/static/assets/portraits/monster_dragon.jpg",
    "/static/assets/portraits/monster_lich.jpg",
    "/static/assets/portraits/monster_golem.jpg",
    "/static/assets/portraits/monster_beholder.jpg",
  ];

  // Board-specific environmental light emitter anchors in normalized (u, v) coordinates
  const BOARD_LIGHT_ANCHORS = {
    "/static/assets/boards/board_sunken_crypt.jpg": [
      { u: 0.19, v: 0.41, r: 0.085, color: "255, 148, 42", phase: 0.2 },
      { u: 0.30, v: 0.30, r: 0.08, color: "255, 158, 54", phase: 1.4 },
      { u: 0.40, v: 0.29, r: 0.08, color: "255, 148, 42", phase: 2.7 },
      { u: 0.36, v: 0.62, r: 0.085, color: "255, 148, 42", phase: 3.9 },
      { u: 0.52, v: 0.42, r: 0.085, color: "255, 152, 48", phase: 5.1 },
      { u: 0.36, v: 0.51, r: 0.13, color: "251, 191, 36", phase: 0.8 }, // Golden Rune Circle
      { u: 0.85, v: 0.29, r: 0.14, color: "56, 189, 248", phase: 2.1 }, // Arcane Blue Portal
    ],
    "/static/assets/boards/board_sky_galleon.jpg": [
      { u: 0.37, v: 0.36, r: 0.13, color: "56, 189, 248", phase: 0.5 }, // Port Aether Cannon
      { u: 0.66, v: 0.61, r: 0.14, color: "56, 189, 248", phase: 2.2 }, // Starboard Aether Cannon
      { u: 0.54, v: 0.49, r: 0.12, color: "251, 191, 36", phase: 1.1 }, // Brass Clockwork Core
      { u: 0.21, v: 0.43, r: 0.07, color: "255, 165, 58", phase: 3.4 },
      { u: 0.47, v: 0.75, r: 0.07, color: "255, 165, 58", phase: 4.8 },
    ],
    "/static/assets/boards/board_dragon_lair.jpg": [
      { u: 0.33, v: 0.21, r: 0.14, color: "249, 115, 22", phase: 0.3 }, // Lava Falls
      { u: 0.16, v: 0.44, r: 0.09, color: "255, 150, 40", phase: 1.7 }, // Skull Altar Brazier L
      { u: 0.30, v: 0.31, r: 0.09, color: "255, 150, 40", phase: 2.9 }, // Skull Altar Brazier R
      { u: 0.50, v: 0.79, r: 0.095, color: "255, 145, 35", phase: 4.1 }, // South Brazier
      { u: 0.87, v: 0.55, r: 0.14, color: "249, 115, 22", phase: 5.3 }, // East Magma River
      { u: 0.62, v: 0.35, r: 0.15, color: "250, 204, 21", phase: 1.2 }, // Golden Dragon Hoard
    ],
  };

  // Isometric Diamond Grid Basis in Normalized Board Coordinates (u, v in [0, 1])
  // Maps the 16x12 tactical grid across all 4 chambers of the painted isometric dungeon floor
  const ISO_CENTER_U = 0.505;
  const ISO_CENTER_V = 0.495;
  const ISO_UX = 0.0285;
  const ISO_UY = 0.0145;
  const ISO_VX = -0.0145;
  const ISO_VY = 0.0315;
  const ISO_DET = ISO_UX * ISO_VY - ISO_UY * ISO_VX;

  class DungeonBattlemap3D {
    constructor(canvasId) {
      this.canvasId = canvasId;
      this.canvas = null;
      this.ctx2d = null;
      this.webglEnabled = false;

      this.gridWidth = 16;
      this.gridHeight = 12;
      this.campaign = null;
      this.tileMeshes = [];

      this._lastClientW = 0;
      this._lastClientH = 0;
      this._lastDpr = 0;

      // Camera View State for Painted Isometric Board (Supports Orbit, Hero Cam, Dragon Cam, Top-Down, Pan & Zoom)
      this.camMode = "orbit";
      this.camZoom = 1.0;
      this.camGoalZoom = 1.0;
      this.camCenterU = 0.5;
      this.camCenterV = 0.5;
      this.camGoalCenterU = 0.5;
      this.camGoalCenterV = 0.5;
      this.shakeIntensity = 0;

      // Pointer interaction state
      this.isPointerDown = false;
      this.pointerMoved = false;
      this.pointerDownPos = { x: 0, y: 0 };
      this.lastPointerPos = { x: 0, y: 0 };

      this.hoverGrid = null;
      this.selectedUnitId = null;

      // Smoothly animated unit standees: id -> { id, gridX, gridY, drawX, drawY, startX, startY, targetX, targetY, moveProgress, attackAnim, data }
      this.unitModels = {};
      this.activeVfx = [];
      this.floatingTexts = [];

      // Rising ember / arcane dust particles
      this.emberData = [];
      this.imageCache = {};
      this.initialized = false;
    }

    init() {
      if (this.initialized) return true;
      this.canvas = document.getElementById(this.canvasId);
      if (!this.canvas) return false;

      try {
        this.ctx2d = this.canvas.getContext("2d");
      } catch (e) {
        this.ctx2d = null;
      }

      // Hide any legacy WebGL overlay canvas so the Painted Isometric Board is always visible
      const legacyOverlay = this.canvas.parentElement?.querySelector(".webgl-overlay-canvas");
      if (legacyOverlay) {
        legacyOverlay.style.display = "none";
      }

      // Preload all 3 hand-painted 16:9 isometric boards and all character/monster oil portraits
      Object.values(BOARD_ASSETS).forEach((url) => this._getHtmlImage(url));
      PORTRAIT_ASSETS.forEach((url) => this._getHtmlImage(url));

      this._initAmbientParticles();
      this._bindCanvasEvents();

      const w = this.canvas.clientWidth || 960;
      const h = this.canvas.clientHeight || 540;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this._lastClientW = w;
      this._lastClientH = h;
      this._lastDpr = dpr;
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);

      this.initialized = true;
      this._animate();
      return true;
    }

    _getHtmlImage(url) {
      const safeUrl = url || "/static/assets/portraits/hero_paladin.jpg";
      if (this.imageCache[safeUrl]) return this.imageCache[safeUrl];
      const img = new Image();
      img.src = safeUrl;
      this.imageCache[safeUrl] = img;
      return img;
    }

    _getActiveBoardUrl() {
      if (!this.campaign || !this.campaign.battlemap) {
        return BOARD_ASSETS.sunken_obsidian_crypt;
      }
      const biomeId = this.campaign.battlemap.biome_id || "sunken_obsidian_crypt";
      if ( this.campaign.id === "camp_rustport_brawl" && biomeId === "rustport_tavern_brawl") {
        return "/static/assets/boards/board_dragon_lair.jpg";
      }
      return BOARD_ASSETS[biomeId] || BOARD_ASSETS.sunken_obsidian_crypt;
    }

    _initAmbientParticles() {
      this.emberData = [];
      for (let i = 0; i < 56; i++) {
        this.emberData.push({
          u: 0.12 + Math.random() * 0.76,
          v: 0.14 + Math.random() * 0.74,
          speedV: 0.018 + Math.random() * 0.032,
          swayAmp: 0.004 + Math.random() * 0.008,
          swayFreq: 1.2 + Math.random() * 2.2,
          phase: Math.random() * Math.PI * 2,
          size: 1.6 + Math.random() * 2.4,
          kind: i % 5 === 0 ? "arcane" : "ember",
        });
      }
    }

    /* ==================== COORDINATE PROJECTION & INVERSE PICKING ==================== */
    gridToWorld(gx, gy) {
      const wx = (gx - (this.gridWidth - 1) / 2) * TILE_SIZE;
      const wz = (gy - (this.gridHeight - 1) / 2) * TILE_SIZE;
      return { x: wx, z: wz };
    }

    // Converts fractional grid coordinate (gx, gy) -> normalized board coordinate (u, v)
    _gridToNormalizedUV(gx, gy) {
      const dx = gx - this.gridWidth * 0.5;
      const dy = gy - this.gridHeight * 0.5;
      return {
        u: ISO_CENTER_U + dx * ISO_UX + dy * ISO_UY,
        v: ISO_CENTER_V + dx * ISO_VX + dy * ISO_VY,
      };
    }

    // Converts normalized board coordinate (u, v) -> canvas pixel (sx, sy) with active camera zoom & pan
    _uvToScreen(u, v, cw, ch) {
      const sx = (u - this.camCenterU) * this.camZoom * cw + cw * 0.5;
      const sy = (v - this.camCenterV) * this.camZoom * ch + ch * 0.5;
      return { sx, sy };
    }

    // Converts canvas pixel (sx, sy) -> normalized board coordinate (u, v)
    _screenToUV(sx, sy, cw, ch) {
      const u = (sx - cw * 0.5) / (this.camZoom * cw) + this.camCenterU;
      const v = (sy - ch * 0.5) / (this.camZoom * ch) + this.camCenterV;
      return { u, v };
    }

    // Projects fractional grid (gx, gy) + vertical pixel lift -> screen (sx, sy)
    _projectIsoGrid(gx, gy, liftPx, cw, ch) {
      const uv = this._gridToNormalizedUV(gx, gy);
      const scr = this._uvToScreen(uv.u, uv.v, cw, ch);
      return {
        sx: scr.sx,
        sy: scr.sy - (liftPx || 0) * this.camZoom,
        u: uv.u,
        v: uv.v,
      };
    }

    _projectWorldToScreen(wx, wy, wz, cw, ch) {
      const gx = wx / TILE_SIZE + (this.gridWidth - 1) / 2 + 0.5;
      const gy = wz / TILE_SIZE + (this.gridHeight - 1) / 2 + 0.5;
      return this._projectIsoGrid(gx, gy, wy * 14, cw, ch);
    }

    _pickTileFromEvent(e) {
      if (!this.canvas) return null;
      const rect = this.canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;

      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const { u, v } = this._screenToUV(sx, sy, rect.width, rect.height);

      const du = u - ISO_CENTER_U;
      const dv = v - ISO_CENTER_V;
      const dx = (ISO_VY * du - ISO_UY * dv) / ISO_DET;
      const dy = (-ISO_VX * du + ISO_UX * dv) / ISO_DET;

      const gx = Math.floor(dx + this.gridWidth * 0.5);
      const gy = Math.floor(dy + this.gridHeight * 0.5);

      if (gx >= 0 && gx < this.gridWidth && gy >= 0 && gy < this.gridHeight) {
        return { gridX: gx, gridY: gy };
      }
      return null;
    }

    /* ==================== CAMPAIGN & MINIATURE SYNCHRONIZATION ==================== */
    _collectCampaignUnits(campaign) {
      const bmap = campaign.battlemap;
      const hero = campaign.hero;
      const units = [];

      units.push({
        id: hero.id || "hero_main",
        name: hero.name,
        side: "hero",
        x: bmap.hero_pos.x,
        y: bmap.hero_pos.y,
        hp: hero.hp,
        max_hp: hero.max_hp,
        ac: hero.ac,
        portrait: hero.portrait || "/static/assets/portraits/hero_paladin.jpg",
        miniature: hero.miniature || "paladin",
        symbol: hero.token_symbol || "🛡️",
      });

      (campaign.npcs || []).forEach((n) => {
        units.push({
          id: n.id,
          name: n.name,
          side: "npc",
          x: n.x,
          y: n.y,
          hp: 24,
          max_hp: 24,
          ac: 14,
          portrait: n.portrait || "/static/assets/portraits/hero_wizard.jpg",
          miniature: n.miniature || "wizard",
          symbol: n.symbol || "🕯️",
        });
      });

      (campaign.monsters || []).forEach((m) => {
        if (m.hp <= 0) return;
        units.push({
          id: m.id,
          name: m.name,
          side: "monster",
          x: m.x,
          y: m.y,
          hp: m.hp,
          max_hp: m.max_hp,
          ac: m.ac,
          portrait: m.portrait || "/static/assets/portraits/monster_dragon.jpg",
          miniature: m.miniature || "dragon",
          symbol: m.symbol || "🐉",
        });
      });

      return units;
    }

    syncCampaign(campaign) {
      if (!this.initialized && !this.init()) return;
      if (!campaign || !campaign.battlemap) return;

      this.campaign = campaign;
      const bmap = campaign.battlemap;
      this.gridWidth = bmap.width || 16;
      this.gridHeight = bmap.height || 12;
      this.tileMeshes = (bmap.tiles || []).map((row, y) =>
        row.map((cell, x) => ({ gridX: x, gridY: y, kind: cell.kind }))
      );

      const units = this._collectCampaignUnits(campaign);
      const activeIds = new Set(units.map((u) => u.id));

      Object.keys(this.unitModels).forEach((id) => {
        if (!activeIds.has(id)) {
          delete this.unitModels[id];
        }
      });

      units.forEach((u) => {
        const wPos = this.gridToWorld(u.x, u.y);
        let existing = this.unitModels[u.id];
        if (!existing) {
          this.unitModels[u.id] = {
            id: u.id,
            side: u.side,
            archetype: u.miniature,
            gridX: u.x,
            gridY: u.y,
            drawX: u.x,
            drawY: u.y,
            startX: u.x,
            startY: u.y,
            targetX: u.x,
            targetY: u.y,
            moveProgress: 1.0,
            attackAnim: 0,
            worldPos: wPos,
            data: u,
          };
        } else {
          if (existing.gridX !== u.x || existing.gridY !== u.y) {
            existing.startX = existing.drawX;
            existing.startY = existing.drawY;
            existing.targetX = u.x;
            existing.targetY = u.y;
            existing.moveProgress = 0.0;
            existing.gridX = u.x;
            existing.gridY = u.y;
          }
          if (existing.data && u.hp < existing.data.hp) {
            const dmg = existing.data.hp - u.hp;
            this.spawnFloatingText(`-${dmg} HP 💥`, { x: wPos.x, y: 2.3, z: wPos.z }, "#ef4444");
          } else if (existing.data && u.hp > existing.data.hp) {
            const heal = u.hp - existing.data.hp;
            this.spawnFloatingText(`+${heal} HP ✨`, { x: wPos.x, y: 2.3, z: wPos.z }, "#10b981");
          }
          existing.worldPos = wPos;
          existing.data = u;
          existing.archetype = u.miniature;
        }
      });

      if (this.camMode === "hero" || this.camMode === "boss") {
        this.setCameraMode(this.camMode);
      }

      const cw = this.canvas.clientWidth || 960;
      const ch = this.canvas.clientHeight || 540;
      this._renderPaintedIsometricBoard(performance.now(), cw, ch);
    }

    /* ==================== CAMERA PRESETS ==================== */
    setCameraMode(mode) {
      this.camMode = mode;
      if (!this.campaign || !this.campaign.battlemap) return;
      const bmap = this.campaign.battlemap;

      if (mode === "hero") {
        const hp = bmap.hero_pos;
        const uv = this._gridToNormalizedUV(hp.x + 0.5, hp.y + 0.5);
        this.camGoalZoom = 1.46;
        this.camGoalCenterU = Math.max(0.28, Math.min(0.72, uv.u));
        this.camGoalCenterV = Math.max(0.28, Math.min(0.72, uv.v - 0.03));
      } else if (mode === "boss") {
        const monsters = (this.campaign.monsters || []).filter((m) => m.hp > 0);
        const boss = monsters.find((m) => m.miniature === "dragon") || monsters[0];
        if (boss) {
          const uv = this._gridToNormalizedUV(boss.x + 0.5, boss.y + 0.5);
          this.camGoalZoom = 1.46;
          this.camGoalCenterU = Math.max(0.28, Math.min(0.72, uv.u));
          this.camGoalCenterV = Math.max(0.28, Math.min(0.72, uv.v - 0.03));
        }
      } else if (mode === "topdown") {
        this.camGoalZoom = 1.15;
        this.camGoalCenterU = 0.51;
        this.camGoalCenterV = 0.49;
      } else {
        // Default 3D Orbit: Full-frame 16:9 painted isometric tabletop view
        this.camGoalZoom = 1.0;
        this.camGoalCenterU = 0.5;
        this.camGoalCenterV = 0.5;
      }
    }

    /* ==================== SPELL & 3D POLYHEDRAL DICE VFX ==================== */
    triggerFireballVFX(targetGrid = null) {
      if (!this.campaign) return;
      const hp = this.campaign.battlemap.hero_pos;
      if (!targetGrid) {
        const monsters = (this.campaign.monsters || []).filter((m) => m.hp > 0);
        const targetMon = monsters.find((m) => m.miniature === "dragon") || monsters[0];
        targetGrid = targetMon ? { x: targetMon.x, y: targetMon.y } : { x: 11, y: 8 };
      }

      const heroUnit = this.unitModels[this.campaign.hero.id];
      if (heroUnit) heroUnit.attackAnim = 1.0;

      const endW = this.gridToWorld(targetGrid.x, targetGrid.y);
      const particles = [];
      for (let i = 0; i < 42; i++) {
        const ang = (Math.PI * 2 * i) / 42 + (Math.random() - 0.5) * 0.25;
        const spd = 28 + Math.random() * 95;
        particles.push({
          vx: Math.cos(ang) * spd,
          vy: Math.sin(ang) * spd * 0.65 - 18,
          size: 2.5 + Math.random() * 4.0,
          color: i % 3 === 0 ? "#fef08a" : i % 2 === 0 ? "#f97316" : "#ef4444",
        });
      }

      this.activeVfx.push({
        type: "fireball",
        fromGrid: { x: hp.x + 0.5, y: hp.y + 0.5 },
        toGrid: { x: targetGrid.x + 0.5, y: targetGrid.y + 0.5 },
        particles,
        born: performance.now(),
        duration: 1150,
        shook: false,
        endW,
      });
    }

    triggerChainLightningVFX() {
      if (!this.campaign) return;
      const hp = this.campaign.battlemap.hero_pos;
      const monsters = (this.campaign.monsters || []).filter((m) => m.hp > 0);
      const targetsGrid =
        monsters.length > 0
          ? monsters.map((m) => ({ x: m.x + 0.5, y: m.y + 0.5 }))
          : [
              { x: 11.5, y: 8.5 },
              { x: 5.5, y: 8.5 },
            ];

      const startW = this.gridToWorld(hp.x, hp.y);
      this.shakeIntensity = 7.0;
      this.spawnFloatingText("⚡ CHAIN LIGHTNING ARC!", { x: startW.x, y: 2.6, z: startW.z }, "#38bdf8");

      this.activeVfx.push({
        type: "lightning",
        fromGrid: { x: hp.x + 0.5, y: hp.y + 0.5 },
        targetsGrid,
        born: performance.now(),
        duration: 850,
      });
    }

    triggerDivineHealVFX(atGrid = null) {
      if (!this.campaign) return;
      const pos = atGrid || this.campaign.battlemap.hero_pos;
      const wPos = this.gridToWorld(pos.x, pos.y);
      this.spawnFloatingText("✨ DIVINE CELESTIAL SMITE!", { x: wPos.x, y: 2.7, z: wPos.z }, "#fde047");

      this.activeVfx.push({
        type: "heal",
        atGrid: { x: pos.x + 0.5, y: pos.y + 0.5 },
        born: performance.now(),
        duration: 1100,
      });
    }

    trigger3DDiceRoll(sides = 20, totalValue = 20, isCrit = false, isFumble = false) {
      const hp = this.campaign ? this.campaign.battlemap.hero_pos : { x: 4, y: 4 };
      const heroW = this.gridToWorld(hp.x, hp.y);
      const label = isCrit
        ? `🎲 NAT 20! CRIT (${totalValue})`
        : isFumble
        ? `🎲 NAT 1! FUMBLE (${totalValue})`
        : `🎲 Rolled d${sides} = ${totalValue}`;
      const col = isCrit ? "#fde047" : isFumble ? "#ef4444" : "#38bdf8";

      this.activeVfx.push({
        type: "dice",
        sides,
        totalValue,
        isCrit,
        isFumble,
        fromGrid: { x: Math.max(1.5, hp.x - 1.5), y: Math.min(10.5, hp.y + 1.5) },
        toGrid: { x: Math.min(13.5, hp.x + 2.5), y: Math.max(2.0, hp.y - 0.5) },
        born: performance.now(),
        duration: 1650,
        popped: false,
        label,
        col,
        heroW,
      });
    }

    spawnFloatingText(text, worldPos, color = "#fde047") {
      this.floatingTexts.push({
        text,
        worldPos: { ...worldPos },
        color,
        born: performance.now(),
        duration: 1550,
      });
    }

    /* ==================== POINTER & WHEEL INTERACTION ==================== */
    _bindCanvasEvents() {
      const c = this.canvas;

      c.addEventListener("pointerdown", (e) => {
        this.isPointerDown = true;
        this.pointerMoved = false;
        this.pointerDownPos = { x: e.clientX, y: e.clientY };
        this.lastPointerPos = { x: e.clientX, y: e.clientY };
      });

      window.addEventListener("pointerup", () => {
        this.isPointerDown = false;
      });

      c.addEventListener("pointermove", (e) => {
        const rect = c.getBoundingClientRect();
        if (this.isPointerDown) {
          const dx = e.clientX - this.lastPointerPos.x;
          const dy = e.clientY - this.lastPointerPos.y;
          if (Math.hypot(e.clientX - this.pointerDownPos.x, e.clientY - this.pointerDownPos.y) > 5) {
            this.pointerMoved = true;
          }
          if (this.camGoalZoom > 1.01) {
            const maxOffset = Math.max(0, (1 - 1 / this.camGoalZoom) * 0.48);
            this.camGoalCenterU = Math.max(
              0.5 - maxOffset,
              Math.min(0.5 + maxOffset, this.camGoalCenterU - dx / (rect.width * this.camGoalZoom))
            );
            this.camGoalCenterV = Math.max(
              0.5 - maxOffset,
              Math.min(0.5 + maxOffset, this.camGoalCenterV - dy / (rect.height * this.camGoalZoom))
            );
          }
          this.lastPointerPos = { x: e.clientX, y: e.clientY };
          return;
        }

        const hit = this._pickTileFromEvent(e);
        if (hit && typeof hit.gridX === "number" && typeof hit.gridY === "number") {
          this.hoverGrid = { x: hit.gridX, y: hit.gridY };
          if (this.campaign) {
            const bmap = this.campaign.battlemap;
            const hx = bmap.hero_pos.x;
            const hy = bmap.hero_pos.y;
            const distFt = Math.round(Math.hypot(hit.gridX - hx, hit.gridY - hy) * 5);
            const cell = bmap.tiles[hit.gridY]?.[hit.gridX];
            const colLetter = String.fromCharCode(65 + hit.gridX);
            const pill = document.getElementById("hoverRangePill");
            if (pill && cell) {
              pill.textContent = `Isometric Tile ${colLetter}${hit.gridY + 1} (${hit.gridX}, ${hit.gridY}) [${cell.kind.toUpperCase()}] • Range: ${distFt} ft`;
            }
          }
        } else {
          this.hoverGrid = null;
        }
      });

      c.addEventListener(
        "wheel",
        (e) => {
          e.preventDefault();
          const nextZoom = Math.max(1.0, Math.min(1.85, this.camGoalZoom - e.deltaY * 0.0012));
          this.camGoalZoom = nextZoom;
          const maxOffset = Math.max(0, (1 - 1 / nextZoom) * 0.48);
          this.camGoalCenterU = Math.max(0.5 - maxOffset, Math.min(0.5 + maxOffset, this.camGoalCenterU));
          this.camGoalCenterV = Math.max(0.5 - maxOffset, Math.min(0.5 + maxOffset, this.camGoalCenterV));
        },
        { passive: false }
      );

      c.addEventListener("click", (e) => {
        if (this.pointerMoved) return;
        const hit = this._pickTileFromEvent(e);
        if (hit && typeof hit.gridX === "number" && typeof hit.gridY === "number") {
          if (typeof window.moveHeroToTile === "function") {
            window.moveHeroToTile(hit.gridX, hit.gridY);
          }
        }
      });
    }

    /* ==================== PRIMARY 60FPS PAINTED ISOMETRIC BOARD RENDERER ==================== */
    _renderPaintedIsometricBoard(now, cw, ch) {
      if (!this.ctx2d) return;
      const ctx = this.ctx2d;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const elapsed = now * 0.001;

      // Smoothly interpolate camera zoom & pan
      this.camZoom += (this.camGoalZoom - this.camZoom) * 0.14;
      this.camCenterU += (this.camGoalCenterU - this.camCenterU) * 0.14;
      this.camCenterV += (this.camGoalCenterV - this.camCenterV) * 0.14;

      let shakeX = 0;
      let shakeY = 0;
      if (this.shakeIntensity > 0.1) {
        shakeX = (Math.random() - 0.5) * this.shakeIntensity;
        shakeY = (Math.random() - 0.5) * this.shakeIntensity;
        this.shakeIntensity *= 0.86;
      } else {
        this.shakeIntensity = 0;
      }

      ctx.save();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";

      // 1. Dark Obsidian Sanctuary Backdrop
      ctx.fillStyle = "#0b0806";
      ctx.fillRect(0, 0, cw, ch);

      // 2. Render Full-Frame 16:9 Hand-Painted Isometric D&D Battlemap Artwork
      const boardUrl = this._getActiveBoardUrl();
      const boardImg = this._getHtmlImage(boardUrl);
      const topLeft = this._uvToScreen(0, 0, cw, ch);
      const drawW = cw * this.camZoom;
      const drawH = ch * this.camZoom;
      const drawX = topLeft.sx + shakeX;
      const drawY = topLeft.sy + shakeY;

      if (boardImg && boardImg.complete && boardImg.naturalWidth > 0) {
        ctx.drawImage(boardImg, drawX, drawY, drawW, drawH);
      } else {
        const fallbackGrad = ctx.createRadialGradient(cw * 0.5, ch * 0.5, 40, cw * 0.5, ch * 0.5, cw * 0.65);
        fallbackGrad.addColorStop(0, "#2b1e16");
        fallbackGrad.addColorStop(1, "#0f0a07");
        ctx.fillStyle = fallbackGrad;
        ctx.fillRect(0, 0, cw, ch);
      }

      // 3. Dynamic Flickering Torchlight, Arcane Rune & Portal Glow Halos
      const lightAnchors = BOARD_LIGHT_ANCHORS[boardUrl] || BOARD_LIGHT_ANCHORS["/static/assets/boards/board_sunken_crypt.jpg"];
      ctx.save();
      ctx.globalCompositeOperation = "screen";
      lightAnchors.forEach((L) => {
        const scr = this._uvToScreen(L.u, L.v, cw, ch);
        const lx = scr.sx + shakeX;
        const ly = scr.sy + shakeY;
        const pulse = 1.0 + Math.sin(elapsed * 6.5 + L.phase) * 0.14 + Math.cos(elapsed * 11.2 + L.phase) * 0.08;
        const rad = L.r * cw * this.camZoom * pulse;
        const alpha = 0.24 + Math.sin(elapsed * 7.2 + L.phase) * 0.06;

        const grad = ctx.createRadialGradient(lx, ly, 2, lx, ly, rad);
        grad.addColorStop(0, `rgba(255, 250, 220, ${Math.min(0.48, alpha * 1.4)})`);
        grad.addColorStop(0.35, `rgba(${L.color}, ${alpha})`);
        grad.addColorStop(1, `rgba(${L.color}, 0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(lx, ly, rad, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();

      if (!this.campaign || !this.campaign.battlemap) {
        ctx.restore();
        return;
      }

      const bmap = this.campaign.battlemap;
      const revealedSet = new Set((bmap.revealed || []).map((p) => `${p[0]},${p[1]}`));
      const visibleSet = new Set((bmap.visible || []).map((p) => `${p[0]},${p[1]}`));
      const fogOn = Boolean(bmap.fog_of_war);
      const isTopDown = this.camMode === "topdown";

      // 4. Project 16x12 Isometric Diamond Tactical Grid & Interactive Props
      for (let y = 0; y < this.gridHeight; y++) {
        for (let x = 0; x < this.gridWidth; x++) {
          const cell = bmap.tiles[y]?.[x];
          if (!cell) continue;

          const p00 = this._projectIsoGrid(x, y, 0, cw, ch);
          const p10 = this._projectIsoGrid(x + 1, y, 0, cw, ch);
          const p11 = this._projectIsoGrid(x + 1, y + 1, 0, cw, ch);
          const p01 = this._projectIsoGrid(x, y + 1, 0, cw, ch);
          const pc = this._projectIsoGrid(x + 0.5, y + 0.5, 0, cw, ch);

          const key = `${x},${y}`;
          const isVis = !fogOn || visibleSet.has(key);
          const isRev = !fogOn || revealedSet.has(key);

          ctx.beginPath();
          ctx.moveTo(p00.sx + shakeX, p00.sy + shakeY);
          ctx.lineTo(p10.sx + shakeX, p10.sy + shakeY);
          ctx.lineTo(p11.sx + shakeX, p11.sy + shakeY);
          ctx.lineTo(p01.sx + shakeX, p01.sy + shakeY);
          ctx.closePath();

          // Soft atmospheric fog-of-war veil on unrevealed tiles (never hides painted art!)
          if (fogOn && !isRev) {
            ctx.fillStyle = "rgba(8, 6, 16, 0.36)";
            ctx.fill();
          } else if (fogOn && !isVis) {
            ctx.fillStyle = "rgba(10, 8, 20, 0.16)";
            ctx.fill();
          }

          // Subtle Golden Isometric Tactical Grid Lines on Walkable Tiles
          if (cell.kind !== "wall") {
            ctx.strokeStyle = isTopDown
              ? "rgba(251, 191, 36, 0.46)"
              : isVis
              ? "rgba(251, 191, 36, 0.25)"
              : "rgba(251, 191, 36, 0.13)";
            ctx.lineWidth = isTopDown ? 1.35 : 1.0;
            ctx.stroke();
          } else if (isTopDown) {
            ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }

          // Subtle Interactive Tile Markers (Chests, Hazards, Doors, Portals)
          const cx = pc.sx + shakeX;
          const cy = pc.sy + shakeY;

          if (cell.hazard) {
            const hCol =
              cell.hazard.type === "lava"
                ? "rgba(249, 115, 22, 0.62)"
                : cell.hazard.type === "ice"
                ? "rgba(56, 189, 248, 0.62)"
                : "rgba(192, 132, 252, 0.62)";
            ctx.save();
            ctx.strokeStyle = hCol;
            ctx.lineWidth = 1.6;
            ctx.beginPath();
            ctx.ellipse(
              cx,
              cy,
              11 * this.camZoom,
              6.5 * this.camZoom,
              0,
              0,
              Math.PI * 2
            );
            ctx.stroke();
            ctx.restore();
          }

          if (cell.chest && !cell.chest.opened) {
            const glint = 0.6 + Math.sin(elapsed * 4.5 + x + y) * 0.35;
            ctx.save();
            ctx.fillStyle = `rgba(250, 204, 21, ${glint * 0.32})`;
            ctx.strokeStyle = "#fde047";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.ellipse(cx, cy, 9 * this.camZoom, 5.5 * this.camZoom, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            ctx.restore();
          }

          if (cell.kind === "exit") {
            const spin = elapsed * 2.2;
            ctx.save();
            ctx.strokeStyle = "rgba(56, 189, 248, 0.82)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.ellipse(cx, cy, 13 * this.camZoom, 7.5 * this.camZoom, 0, spin, spin + Math.PI * 1.4);
            ctx.stroke();
            ctx.restore();
          }
        }
      }

      // 5. Isometric Coordinate Markers (A–P and 1–12) Along Outer Grid Rim
      ctx.save();
      ctx.font = `700 ${Math.round(9.5 * Math.sqrt(this.camZoom))}px Cinzel, Georgia, serif`;
      ctx.fillStyle = "rgba(253, 230, 138, 0.78)";
      ctx.shadowColor = "rgba(0, 0, 0, 0.95)";
      ctx.shadowBlur = 4;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (let x = 0; x < this.gridWidth; x += 2) {
        const lbl = String.fromCharCode(65 + x);
        const pt = this._projectIsoGrid(x + 0.5, -0.45, 0, cw, ch);
        ctx.fillText(lbl, pt.sx + shakeX, pt.sy + shakeY);
      }
      for (let y = 0; y < this.gridHeight; y += 2) {
        const lbl = String(y + 1);
        const pt = this._projectIsoGrid(-0.55, y + 0.5, 0, cw, ch);
        ctx.fillText(lbl, pt.sx + shakeX, pt.sy + shakeY);
      }
      ctx.restore();

      // 6. Hero Active Tile Highlight & Hovered Tile Isometric Target Diamond
      const heroPos = bmap.hero_pos;
      this._drawIsometricTileHighlight(
        ctx,
        heroPos.x,
        heroPos.y,
        "#38bdf8",
        "rgba(56, 189, 248, 0.22)",
        cw,
        ch,
        shakeX,
        shakeY,
        elapsed
      );

      if (this.hoverGrid) {
        this._drawIsometricTileHighlight(
          ctx,
          this.hoverGrid.x,
          this.hoverGrid.y,
          "#facc15",
          "rgba(250, 204, 21, 0.28)",
          cw,
          ch,
          shakeX,
          shakeY,
          elapsed
        );

        // Tactical Range Line from Hero to Hovered Tile
        if (this.hoverGrid.x !== heroPos.x || this.hoverGrid.y !== heroPos.y) {
          const hScr = this._projectIsoGrid(heroPos.x + 0.5, heroPos.y + 0.5, 2, cw, ch);
          const tScr = this._projectIsoGrid(this.hoverGrid.x + 0.5, this.hoverGrid.y + 0.5, 2, cw, ch);
          ctx.save();
          ctx.setLineDash([5, 4]);
          ctx.strokeStyle = "rgba(250, 204, 21, 0.78)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(hScr.sx + shakeX, hScr.sy + shakeY);
          ctx.lineTo(tScr.sx + shakeX, tScr.sy + shakeY);
          ctx.stroke();
          ctx.restore();
        }
      }

      // 7. Update & Sort All 3D Miniature Standees Back-to-Front by Isometric Screen Y
      const rawUnits = Object.values(this.unitModels).map((u, idx) => {
        if (u.moveProgress < 1.0) {
          u.moveProgress = Math.min(1.0, u.moveProgress + 0.09);
          const t = u.moveProgress;
          u.drawX = u.startX + (u.targetX - u.startX) * t;
          u.drawY = u.startY + (u.targetY - u.startY) * t;
        } else {
          u.drawX = u.gridX;
          u.drawY = u.gridY;
        }
        const hopPx = u.moveProgress < 1.0 ? Math.sin(u.moveProgress * Math.PI) * 28 : 0;
        const bobPx = Math.sin(elapsed * 2.9 + idx * 1.4) * 2.2;
        const proj = this._projectIsoGrid(u.drawX + 0.5, u.drawY + 0.5, hopPx, cw, ch);
        return {
          unit: u,
          sx: proj.sx + shakeX,
          sy: proj.sy + shakeY,
          bobPx,
        };
      });

      // Gentle 3-pass screen-space separation so adjacent miniatures never overlap each other's portraits/labels
      const minSep = 78 * Math.min(1.25, Math.max(0.9, this.camZoom));
      for (let pass = 0; pass < 3; pass++) {
        for (let i = 0; i < rawUnits.length; i++) {
          for (let j = i + 1; j < rawUnits.length; j++) {
            const a = rawUnits[i];
            const b = rawUnits[j];
            const dx = b.sx - a.sx;
            const dy = b.sy - a.sy;
            const dist = Math.hypot(dx, dy);
            if (dist < minSep && dist > 0.01) {
              const push = (minSep - dist) * 0.52;
              const nx = dx / dist;
              const ny = dy / dist;
              a.sx -= nx * push;
              a.sy -= ny * push * 0.72;
              b.sx += nx * push;
              b.sy += ny * push * 0.72;
            }
          }
        }
      }

      const sortedUnits = rawUnits.sort((a, b) => a.sy - b.sy);

      sortedUnits.forEach((item) => {
        this._drawSculptedMiniatureStandee(ctx, item.unit, item.sx, item.sy, item.bobPx, elapsed);
      });

      // 8. Rising Ambient Ember & Arcane Mote Particles
      this._renderAmbientParticles(ctx, elapsed, cw, ch, shakeX, shakeY);

      // 9. Active 60FPS Spell & 3D Polyhedral Dice VFX
      this._renderActiveSpellVfx(ctx, now, cw, ch, shakeX, shakeY);

      // 10. Ornate Burnished-Gold Inner Vignette Border
      ctx.strokeStyle = "rgba(245, 158, 11, 0.55)";
      ctx.lineWidth = 2;
      ctx.strokeRect(1, 1, cw - 2, ch - 2);

      ctx.restore();
    }

    _drawIsometricTileHighlight(ctx, gx, gy, strokeColor, fillColor, cw, ch, shakeX, shakeY, elapsed) {
      const p00 = this._projectIsoGrid(gx, gy, 0, cw, ch);
      const p10 = this._projectIsoGrid(gx + 1, gy, 0, cw, ch);
      const p11 = this._projectIsoGrid(gx + 1, gy + 1, 0, cw, ch);
      const p01 = this._projectIsoGrid(gx, gy + 1, 0, cw, ch);
      const pc = this._projectIsoGrid(gx + 0.5, gy + 0.5, 0, cw, ch);

      ctx.save();
      ctx.fillStyle = fillColor;
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.2;
      ctx.shadowColor = strokeColor;
      ctx.shadowBlur = 10;

      ctx.beginPath();
      ctx.moveTo(p00.sx + shakeX, p00.sy + shakeY);
      ctx.lineTo(p10.sx + shakeX, p10.sy + shakeY);
      ctx.lineTo(p11.sx + shakeX, p11.sy + shakeY);
      ctx.lineTo(p01.sx + shakeX, p01.sy + shakeY);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Pulsing inner isometric ring
      const pulse = 1.0 + Math.sin(elapsed * 4.2) * 0.08;
      ctx.beginPath();
      ctx.ellipse(
        pc.sx + shakeX,
        pc.sy + shakeY,
        14 * this.camZoom * pulse,
        8 * this.camZoom * pulse,
        0,
        0,
        Math.PI * 2
      );
      ctx.stroke();
      ctx.restore();
    }

    /* ==================== SCULPTED 3D MINIATURE STANDEE RENDERER ==================== */
    _drawSculptedMiniatureStandee(ctx, u, sx, sy, bobPx, elapsed) {
      const d = u.data;
      if (!d) return;

      const isBoss = d.miniature === "dragon" || d.miniature === "golem";
      const isHero = d.side === "hero";
      const isNpc = d.side === "npc";
      const scale = Math.min(1.38, Math.max(0.88, this.camZoom));

      const baseRx = (isBoss ? 25 : 21) * scale;
      const baseRy = (isBoss ? 12.5 : 10.5) * scale;
      const baseDepth = (isBoss ? 7.5 : 6.5) * scale;
      const standeeR = (isBoss ? 24 : 20) * scale;

      // Attack lunge offset
      let lungeX = 0;
      let lungeY = 0;
      if (u.attackAnim > 0.01) {
        lungeX = Math.sin(u.attackAnim * Math.PI) * 14 * scale;
        lungeY = -Math.sin(u.attackAnim * Math.PI) * 8 * scale;
        u.attackAnim *= 0.85;
      } else {
        u.attackAnim = 0;
      }

      const px = sx + lungeX;
      const py = sy + lungeY;

      const primaryRim = isHero ? "#fbbf24" : isNpc ? "#34d399" : "#ef4444";
      const secondaryGlow = isHero ? "#38bdf8" : isNpc ? "#a855f7" : "#f97316";

      ctx.save();

      // 1. Cast Drop Shadow on the Painted Dungeon Floor
      ctx.fillStyle = "rgba(0, 0, 0, 0.72)";
      ctx.beginPath();
      ctx.ellipse(px, py + 4 * scale, baseRx * 1.18, baseRy * 1.15, 0, 0, Math.PI * 2);
      ctx.fill();

      // 2. Glowing Magic Aura Ring Under Pedestal
      const auraPulse = 1.0 + Math.sin(elapsed * 3.6 + u.gridX) * 0.06;
      ctx.strokeStyle = primaryRim;
      ctx.lineWidth = 1.8 * scale;
      ctx.beginPath();
      ctx.ellipse(px, py + 1 * scale, baseRx * 1.08 * auraPulse, baseRy * 1.08 * auraPulse, 0, 0, Math.PI * 2);
      ctx.stroke();

      // 3. 3D Extruded Sculpted Pedestal Cylinder (Lower Rim + Side Wall + Upper Metallic Bevel)
      const sideGrad = ctx.createLinearGradient(px - baseRx, py, px + baseRx, py);
      if (isHero) {
        sideGrad.addColorStop(0, "#451a03");
        sideGrad.addColorStop(0.5, "#d97706");
        sideGrad.addColorStop(1, "#451a03");
      } else if (isNpc) {
        sideGrad.addColorStop(0, "#064e3b");
        sideGrad.addColorStop(0.5, "#10b981");
        sideGrad.addColorStop(1, "#064e3b");
      } else {
        sideGrad.addColorStop(0, "#450a0a");
        sideGrad.addColorStop(0.5, "#dc2626");
        sideGrad.addColorStop(1, "#450a0a");
      }

      ctx.fillStyle = sideGrad;
      ctx.beginPath();
      ctx.ellipse(px, py + baseDepth, baseRx, baseRy, 0, 0, Math.PI);
      ctx.lineTo(px - baseRx, py);
      ctx.ellipse(px, py, baseRx, baseRy, 0, Math.PI, 0, true);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "#09060e";
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // Pedestal Top Plate (Dark Carved Obsidian Slate)
      const topGrad = ctx.createRadialGradient(px, py - 2 * scale, 2, px, py, baseRx);
      topGrad.addColorStop(0, "#3b2f4a");
      topGrad.addColorStop(1, "#140f1d");
      ctx.fillStyle = topGrad;
      ctx.beginPath();
      ctx.ellipse(px, py, baseRx, baseRy, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = primaryRim;
      ctx.lineWidth = 2.0 * scale;
      ctx.stroke();

      // 4. Upright Sculpted Oil-Painted Portrait Standee Medallion
      const standeeCy = py - standeeR - 5 * scale - Math.max(0, bobPx);

      // Standee Brass Mounting Foot
      ctx.fillStyle = "#b45309";
      ctx.strokeStyle = "#fde68a";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.roundRect(px - 7 * scale, py - 8 * scale, 14 * scale, 8 * scale, 3);
      ctx.fill();
      ctx.stroke();

      // Boss / Hero Back Crest Halo
      ctx.save();
      ctx.shadowColor = primaryRim;
      ctx.shadowBlur = 14;
      const frameGrad = ctx.createLinearGradient(px, standeeCy - standeeR, px, standeeCy + standeeR);
      if (isHero) {
        frameGrad.addColorStop(0, "#fef08a");
        frameGrad.addColorStop(0.5, "#f59e0b");
        frameGrad.addColorStop(1, "#78350f");
      } else if (isNpc) {
        frameGrad.addColorStop(0, "#a7f3d0");
        frameGrad.addColorStop(0.5, "#10b981");
        frameGrad.addColorStop(1, "#064e3b");
      } else {
        frameGrad.addColorStop(0, "#fecaca");
        frameGrad.addColorStop(0.5, "#ef4444");
        frameGrad.addColorStop(1, "#7f1d1d");
      }

      ctx.fillStyle = frameGrad;
      ctx.beginPath();
      ctx.arc(px, standeeCy, standeeR + 3.2 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // Inner Dark Velvet Backdrop + Clipped High-Res Oil Portrait
      ctx.fillStyle = "#120d1c";
      ctx.beginPath();
      ctx.arc(px, standeeCy, standeeR, 0, Math.PI * 2);
      ctx.fill();

      const img = this._getHtmlImage(d.portrait);
      if (img && img.complete && img.naturalWidth > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(px, standeeCy, standeeR - 1.2 * scale, 0, Math.PI * 2);
        ctx.clip();
        ctx.drawImage(
          img,
          px - standeeR,
          standeeCy - standeeR,
          standeeR * 2,
          standeeR * 2
        );
        ctx.restore();
      }

      // Crisp Inner Metallic Rim
      ctx.strokeStyle = isHero ? "#fef3c7" : secondaryGlow;
      ctx.lineWidth = 1.4 * scale;
      ctx.beginPath();
      ctx.arc(px, standeeCy, standeeR - 1 * scale, 0, Math.PI * 2);
      ctx.stroke();

      // 5. Role Crest Badge (Top-Right of Standee) & AC Shield Badge (Bottom-Left)
      const badgeR = 8.5 * scale;
      const bx = px + standeeR * 0.74;
      const by = standeeCy - standeeR * 0.72;
      ctx.fillStyle = "#161024";
      ctx.strokeStyle = primaryRim;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(bx, by, badgeR, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.font = `${Math.round(10 * scale)}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(d.symbol || (isHero ? "🛡️" : isNpc ? "🕯️" : "🐉"), bx, by + 0.5);

      // AC Shield Pill (Bottom-Left of Standee)
      const acX = px - standeeR * 0.78;
      const acY = standeeCy + standeeR * 0.62;
      ctx.fillStyle = "rgba(15, 11, 26, 0.94)";
      ctx.strokeStyle = "#fbbf24";
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.roundRect(acX - 13 * scale, acY - 7 * scale, 26 * scale, 14 * scale, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#fde68a";
      ctx.font = `800 ${Math.round(8.5 * scale)}px "JetBrains Mono", monospace`;
      ctx.fillText(`AC${d.ac}`, acX, acY + 0.5);

      // 6. Sleek Pedestal HP Bar & Compact Non-Overlapping Nameplate
      const hpPct = Math.max(0, Math.min(1, d.hp / Math.max(1, d.max_hp)));
      const barW = 40 * scale;
      const barH = 4.8 * scale;
      const barX = px - barW * 0.5;
      const barY = py + 1.5 * scale;

      ctx.fillStyle = "rgba(9, 6, 15, 0.92)";
      ctx.strokeStyle = "rgba(251, 191, 36, 0.65)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(barX - 1, barY - 1, barW + 2, barH + 2, 3);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = isHero || isNpc ? "#10b981" : "#ef4444";
      ctx.beginPath();
      ctx.roundRect(barX, barY, Math.max(2, barW * hpPct), barH, 2);
      ctx.fill();

      // Compact Short Name Label Directly Under Base
      let shortName = String(d.name || "")
        .replace(/^Echo of /i, "")
        .replace(/^Obsidian /i, "")
        .split(",")[0]
        .split(" the ")[0]
        .trim();
      if (shortName.length > 14) {
        shortName = shortName.slice(0, 13) + "…";
      }
      ctx.font = `800 ${Math.round(9.5 * scale)}px Cinzel, Georgia, serif`;
      const textW = ctx.measureText(shortName).width;
      const pillW = textW + 10 * scale;
      const pillH = 13.5 * scale;
      const pillX = px - pillW * 0.5;
      const pillY = barY + barH + 2.5 * scale;

      ctx.fillStyle = "rgba(10, 7, 18, 0.84)";
      ctx.strokeStyle = primaryRim;
      ctx.lineWidth = 1.1;
      ctx.beginPath();
      ctx.roundRect(pillX, pillY, pillW, pillH, 999);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#fef3c7";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(shortName, px, pillY + pillH * 0.52);

      ctx.restore();
    }

    /* ==================== AMBIENT EMBER & ARCANE PARTICLES ==================== */
    _renderAmbientParticles(ctx, elapsed, cw, ch, shakeX, shakeY) {
      ctx.save();
      this.emberData.forEach((p) => {
        const curV = ((p.v - elapsed * p.speedV) % 0.82 + 0.82) % 0.82 + 0.09;
        const curU = p.u + Math.sin(elapsed * p.swayFreq + p.phase) * p.swayAmp;
        const scr = this._uvToScreen(curU, curV, cw, ch);
        const alpha = Math.sin(((curV - 0.09) / 0.82) * Math.PI) * 0.82;

        ctx.fillStyle =
          p.kind === "arcane"
            ? `rgba(56, 189, 248, ${alpha})`
            : `rgba(251, 191, 36, ${alpha})`;
        ctx.shadowColor = p.kind === "arcane" ? "#38bdf8" : "#f97316";
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.arc(scr.sx + shakeX, scr.sy + shakeY, p.size * Math.sqrt(this.camZoom), 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    }

    /* ==================== 60FPS SPELL & 3D D20 VFX RENDERING ==================== */
    _renderActiveSpellVfx(ctx, now, cw, ch, shakeX, shakeY) {
      for (let i = this.activeVfx.length - 1; i >= 0; i--) {
        const fx = this.activeVfx[i];
        const p = (now - fx.born) / fx.duration;
        if (p >= 1) {
          this.activeVfx.splice(i, 1);
          continue;
        }

        if (fx.type === "fireball") {
          const sProj = this._projectIsoGrid(fx.fromGrid.x, fx.fromGrid.y, 26, cw, ch);
          const eProj = this._projectIsoGrid(fx.toGrid.x, fx.toGrid.y, 18, cw, ch);
          const sx = sProj.sx + shakeX;
          const sy = sProj.sy + shakeY;
          const ex = eProj.sx + shakeX;
          const ey = eProj.sy + shakeY;

          if (p < 0.38) {
            const t = p / 0.38;
            const cx = sx + (ex - sx) * t;
            const cy = sy + (ey - sy) * t - Math.sin(t * Math.PI) * 95 * this.camZoom;

            ctx.save();
            // Blazing comet tail
            for (let k = 1; k <= 6; k++) {
              const tt = Math.max(0, t - k * 0.035);
              const tx = sx + (ex - sx) * tt;
              const ty = sy + (ey - sy) * tt - Math.sin(tt * Math.PI) * 95 * this.camZoom;
              ctx.fillStyle = `rgba(249, 115, 22, ${(1 - k / 7) * 0.55})`;
              ctx.beginPath();
              ctx.arc(tx, ty, (16 - k * 2) * this.camZoom, 0, Math.PI * 2);
              ctx.fill();
            }

            const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, 24 * this.camZoom);
            grad.addColorStop(0, "#ffffff");
            grad.addColorStop(0.35, "#fef08a");
            grad.addColorStop(0.7, "#f97316");
            grad.addColorStop(1, "rgba(239, 68, 68, 0)");
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(cx, cy, 24 * this.camZoom, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
          } else {
            if (!fx.shook) {
              fx.shook = true;
              this.shakeIntensity = 11.0;
              this.spawnFloatingText("🔥 FIREBALL DETONATION! (8d6)", { x: fx.endW.x, y: 2.8, z: fx.endW.z }, "#f97316");
            }
            const t = (p - 0.38) / 0.62;
            const rad = (18 + t * 115) * this.camZoom;

            ctx.save();
            const expGrad = ctx.createRadialGradient(ex, ey, 4, ex, ey, rad);
            expGrad.addColorStop(0, `rgba(255, 255, 255, ${(1 - t) * 0.95})`);
            expGrad.addColorStop(0.3, `rgba(254, 240, 138, ${(1 - t) * 0.85})`);
            expGrad.addColorStop(0.65, `rgba(249, 115, 22, ${(1 - t) * 0.65})`);
            expGrad.addColorStop(1, "rgba(185, 28, 28, 0)");
            ctx.fillStyle = expGrad;
            ctx.beginPath();
            ctx.arc(ex, ey, rad, 0, Math.PI * 2);
            ctx.fill();

            // Isometric shockwave ellipse
            ctx.strokeStyle = `rgba(250, 204, 21, ${1 - t})`;
            ctx.lineWidth = 3.5;
            ctx.beginPath();
            ctx.ellipse(ex, ey, rad * 1.15, rad * 0.62, 0, 0, Math.PI * 2);
            ctx.stroke();

            // Flying explosion sparks
            fx.particles.forEach((pt) => {
              const px = ex + pt.vx * t * this.camZoom;
              const py = ey + (pt.vy * t + 65 * t * t) * this.camZoom;
              ctx.fillStyle = pt.color;
              ctx.globalAlpha = Math.max(0, 1 - t);
              ctx.beginPath();
              ctx.arc(px, py, pt.size * this.camZoom, 0, Math.PI * 2);
              ctx.fill();
            });
            ctx.restore();
          }
        } else if (fx.type === "lightning") {
          const sProj = this._projectIsoGrid(fx.fromGrid.x, fx.fromGrid.y, 28, cw, ch);
          let prevX = sProj.sx + shakeX;
          let prevY = sProj.sy + shakeY;

          ctx.save();
          fx.targetsGrid.forEach((tg) => {
            const tProj = this._projectIsoGrid(tg.x, tg.y, 26, cw, ch);
            const tx = tProj.sx + shakeX;
            const ty = tProj.sy + shakeY;

            for (let strand = 0; strand < 2; strand++) {
              ctx.strokeStyle = strand === 0 ? "#e0f2fe" : "#38bdf8";
              ctx.lineWidth = strand === 0 ? 3.2 : 6.0;
              ctx.shadowColor = "#38bdf8";
              ctx.shadowBlur = 16;
              ctx.globalAlpha = (1 - p * 0.7) * (strand === 0 ? 1 : 0.55);

              ctx.beginPath();
              ctx.moveTo(prevX, prevY);
              const steps = 8;
              for (let s = 1; s < steps; s++) {
                const frac = s / steps;
                const jx = (Math.random() - 0.5) * 26;
                const jy = (Math.random() - 0.5) * 22;
                ctx.lineTo(prevX + (tx - prevX) * frac + jx, prevY + (ty - prevY) * frac + jy);
              }
              ctx.lineTo(tx, ty);
              ctx.stroke();
            }

            // Electric impact burst
            ctx.strokeStyle = `rgba(125, 211, 252, ${1 - p})`;
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.arc(tx, ty, (14 + p * 34) * this.camZoom, 0, Math.PI * 2);
            ctx.stroke();

            prevX = tx;
            prevY = ty;
          });
          ctx.restore();
        } else if (fx.type === "heal") {
          const cProj = this._projectIsoGrid(fx.atGrid.x, fx.atGrid.y, 0, cw, ch);
          const cx = cProj.sx + shakeX;
          const cy = cProj.sy + shakeY;

          ctx.save();
          const pillarW = (38 + Math.sin(p * Math.PI) * 18) * this.camZoom;
          const beamGrad = ctx.createLinearGradient(cx - pillarW, 0, cx + pillarW, 0);
          beamGrad.addColorStop(0, "rgba(250, 204, 21, 0)");
          beamGrad.addColorStop(0.5, `rgba(254, 240, 138, ${(1 - p) * 0.58})`);
          beamGrad.addColorStop(1, "rgba(250, 204, 21, 0)");
          ctx.fillStyle = beamGrad;
          ctx.fillRect(cx - pillarW, 0, pillarW * 2, cy + 12);

          // Rising celestial halo rings
          for (let rIdx = 0; rIdx < 3; rIdx++) {
            const rp = (p * 1.4 + rIdx * 0.28) % 1;
            const ry = cy - rp * 110 * this.camZoom;
            ctx.strokeStyle = rIdx % 2 === 0 ? `rgba(254, 240, 138, ${1 - rp})` : `rgba(52, 211, 153, ${1 - rp})`;
            ctx.lineWidth = 2.8;
            ctx.beginPath();
            ctx.ellipse(cx, ry, 30 * this.camZoom, 15 * this.camZoom, 0, 0, Math.PI * 2);
            ctx.stroke();
          }
          ctx.restore();
        } else if (fx.type === "dice") {
          const sProj = this._projectIsoGrid(fx.fromGrid.x, fx.fromGrid.y, 0, cw, ch);
          const eProj = this._projectIsoGrid(fx.toGrid.x, fx.toGrid.y, 0, cw, ch);
          const moveT = Math.min(1, p / 0.58);
          const bounce =
            p < 0.58
              ? Math.abs(Math.sin(moveT * Math.PI * 2.5)) * (1 - moveT * 0.65) * 75 * this.camZoom
              : 0;

          if (p >= 0.58 && !fx.popped) {
            fx.popped = true;
            this.spawnFloatingText(fx.label, { x: fx.heroW.x, y: 2.6, z: fx.heroW.z }, fx.col);
          }

          const dx = sProj.sx + (eProj.sx - sProj.sx) * moveT + shakeX;
          const dy = sProj.sy + (eProj.sy - sProj.sy) * moveT - bounce + shakeY;
          const rot = p < 0.58 ? moveT * Math.PI * 6 : 0;
          const r = 24 * this.camZoom;

          ctx.save();
          // Die shadow on floor
          ctx.fillStyle = "rgba(0, 0, 0, 0.58)";
          ctx.beginPath();
          ctx.ellipse(dx, dy + bounce + 6, r * 0.85, r * 0.42, 0, 0, Math.PI * 2);
          ctx.fill();

          ctx.translate(dx, dy);
          ctx.rotate(rot);

          // 3D Faceted Icosahedron (d20) Polygon
          const hexPts = [];
          for (let k = 0; k < 6; k++) {
            const ang = (k * Math.PI) / 3 - Math.PI / 2;
            hexPts.push({ x: Math.cos(ang) * r, y: Math.sin(ang) * r });
          }

          const dieGrad = ctx.createRadialGradient(-r * 0.25, -r * 0.25, 2, 0, 0, r);
          if (fx.isCrit) {
            dieGrad.addColorStop(0, "#fef08a");
            dieGrad.addColorStop(0.55, "#d97706");
            dieGrad.addColorStop(1, "#78350f");
          } else if (fx.isFumble) {
            dieGrad.addColorStop(0, "#fca5a5");
            dieGrad.addColorStop(0.55, "#dc2626");
            dieGrad.addColorStop(1, "#450a0a");
          } else {
            dieGrad.addColorStop(0, "#c084fc");
            dieGrad.addColorStop(0.55, "#6d28d9");
            dieGrad.addColorStop(1, "#2e1065");
          }

          ctx.fillStyle = dieGrad;
          ctx.strokeStyle = "#fde68a";
          ctx.lineWidth = 2.2;
          ctx.shadowColor = fx.col;
          ctx.shadowBlur = 14;

          ctx.beginPath();
          hexPts.forEach((pt, idx) => {
            if (idx === 0) ctx.moveTo(pt.x, pt.y);
            else ctx.lineTo(pt.x, pt.y);
          });
          ctx.closePath();
          ctx.fill();
          ctx.stroke();

          // Inner icosahedron triangle facets
          const innerR = r * 0.58;
          const triPts = [0, 1, 2].map((k) => {
            const ang = (k * 2 * Math.PI) / 3 - Math.PI / 2;
            return { x: Math.cos(ang) * innerR, y: Math.sin(ang) * innerR };
          });
          ctx.strokeStyle = "rgba(254, 243, 199, 0.72)";
          ctx.lineWidth = 1.3;
          ctx.beginPath();
          triPts.forEach((pt, idx) => {
            if (idx === 0) ctx.moveTo(pt.x, pt.y);
            else ctx.lineTo(pt.x, pt.y);
          });
          ctx.closePath();
          ctx.stroke();

          ctx.rotate(-rot);
          ctx.fillStyle = "#ffffff";
          ctx.font = `900 ${Math.round(13 * this.camZoom)}px Cinzel, Georgia, serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(String(fx.totalValue), 0, 1);
          ctx.restore();
        }
      }
    }

    /* ==================== 60FPS ANIMATION LOOP ==================== */
    _animate() {
      requestAnimationFrame(() => this._animate());
      if (!this.canvas) return;

      const now = performance.now();
      const cw = this.canvas.clientWidth;
      const ch = this.canvas.clientHeight;
      if (cw === 0 || ch === 0) return;

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (
        Math.abs(cw - this._lastClientW) > 1 ||
        Math.abs(ch - this._lastClientH) > 1 ||
        dpr !== this._lastDpr
      ) {
        this._lastClientW = cw;
        this._lastClientH = ch;
        this._lastDpr = dpr;
        this.canvas.width = Math.round(cw * dpr);
        this.canvas.height = Math.round(ch * dpr);
      }

      this._renderPaintedIsometricBoard(now, cw, ch);
      this._updateFloatingCombatPopups(now, cw, ch);
    }

    _updateFloatingCombatPopups(now, cw, ch) {
      const overlay = document.getElementById("map3dLabelsOverlay");
      if (!overlay) return;

      for (let i = this.floatingTexts.length - 1; i >= 0; i--) {
        const ft = this.floatingTexts[i];
        const age = now - ft.born;
        if (age >= ft.duration) {
          if (ft.el) ft.el.remove();
          this.floatingTexts.splice(i, 1);
          continue;
        }
        if (!ft.el) {
          ft.el = document.createElement("div");
          ft.el.className = "floating-3d-popup";
          ft.el.style.color = ft.color;
          ft.el.textContent = ft.text;
          overlay.appendChild(ft.el);
        }
        const p = age / ft.duration;
        const scr = this._projectWorldToScreen(
          ft.worldPos.x,
          ft.worldPos.y + p * 1.6,
          ft.worldPos.z,
          cw,
          ch
        );
        if (scr) {
          ft.el.style.left = `${scr.sx.toFixed(1)}px`;
          ft.el.style.top = `${(scr.sy - i * 28).toFixed(1)}px`;
          ft.el.style.opacity = (1 - p * p).toFixed(2);
        }
      }
    }
  }

  window.Battlemap3D = new DungeonBattlemap3D("battlemapCanvas");
})();
