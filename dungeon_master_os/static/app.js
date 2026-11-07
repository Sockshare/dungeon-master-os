/* Dungeon Master OS — Client-Side Command Deck, 3D WebGL Dungeon Tabletop, 4-Agent GM & Polyhedral Dice Engine */

const state = {
  catalog: { biomes: [], heroes: [], supported_dice: [4, 6, 8, 10, 12, 20, 100], settings: {} },
  campaigns: [],
  activeCampaign: null,
  activeView: "deck",
  selectedSides: 20,
  diceMode: "normal",
  hoverTile: null,
  audioCtx: null,
  ambientOsc: null,
  ambientPlaying: false,
};

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatSimpleMarkdown(text) {
  let s = esc(text);
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\*(.+?)\*/g, "<em>$1</em>");
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  return s.replace(/\n/g, "<br/>");
}

/* ==================== WEB AUDIO SYNTHESIZER (DICE & SPELL VFX) ==================== */
function getAudioCtx() {
  if (!state.audioCtx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (AC) state.audioCtx = new AC();
  }
  if (state.audioCtx && state.audioCtx.state === "suspended") {
    state.audioCtx.resume().catch(() => {});
  }
  return state.audioCtx;
}

function playDiceClatterSfx() {
  try {
    const ctx = getAudioCtx();
    if (!ctx) return;
    const now = ctx.currentTime;
    [0, 0.055, 0.11, 0.17].forEach((offset, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(320 + idx * 110, now + offset);
      osc.frequency.exponentialRampToValueAtTime(140, now + offset + 0.045);
      gain.gain.setValueAtTime(0.12, now + offset);
      gain.gain.exponentialRampToValueAtTime(0.001, now + offset + 0.048);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + offset);
      osc.stop(now + offset + 0.05);
    });
  } catch (_) {}
}

function playCritFanfareSfx() {
  try {
    const ctx = getAudioCtx();
    if (!ctx) return;
    const now = ctx.currentTime;
    const notes = [523.25, 659.25, 783.99, 1046.5];
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(freq, now + i * 0.08);
      gain.gain.setValueAtTime(0.11, now + i * 0.08);
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + 0.26);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + i * 0.08);
      osc.stop(now + i * 0.08 + 0.28);
    });
  } catch (_) {}
}

function playFumbleSfx() {
  try {
    const ctx = getAudioCtx();
    if (!ctx) return;
    const now = ctx.currentTime;
    [220, 164.81, 110].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(freq, now + i * 0.11);
      gain.gain.setValueAtTime(0.1, now + i * 0.11);
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.11 + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + i * 0.11);
      osc.stop(now + i * 0.11 + 0.27);
    });
  } catch (_) {}
}

function playSpellBoomSfx() {
  try {
    const ctx = getAudioCtx();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(190, now);
    osc.frequency.exponentialRampToValueAtTime(42, now + 0.42);
    gain.gain.setValueAtTime(0.18, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.46);
  } catch (_) {}
}

function toggleAmbientSoundscape() {
  const btn = document.getElementById("ambientAudioBtn");
  try {
    const ctx = getAudioCtx();
    if (!ctx) return;
    if (state.ambientPlaying && state.ambientOsc) {
      state.ambientOsc.stop();
      state.ambientOsc.disconnect();
      state.ambientOsc = null;
      state.ambientPlaying = false;
      btn.textContent = "🔊 Soundscape: Muted";
      return;
    }
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(65.41, ctx.currentTime);
    gain.gain.setValueAtTime(0.035, ctx.currentTime);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    state.ambientOsc = osc;
    state.ambientPlaying = true;
    btn.textContent = "🎶 Soundscape: Active";
  } catch (_) {}
}

/* ==================== API HELPERS ==================== */
async function apiFetch(url, options = {}) {
  const opts = { ...options };
  if (opts.body && typeof opts.body === "object") {
    opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    opts.body = JSON.stringify(opts.body);
  }
  const resp = await fetch(url, opts);
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(errText || `HTTP ${resp.status}`);
  }
  return resp.json();
}

/* ==================== VIEW NAVIGATION ==================== */
function switchView(viewName) {
  state.activeView = viewName;
  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.toggle("active", sec.id === `view-${viewName}`);
  });
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });
  if (viewName === "campaigns" && state.activeCampaign) {
    refreshChronicleExportPreview();
  }
  if (viewName === "dice") {
    refreshDiceStats();
  }
}

/* ==================== 3D WEBGL BATTLEMAP BRIDGE ==================== */
function renderBattlemapCanvas() {
  if (!state.activeCampaign) return;
  if (window.Battlemap3D && window.Battlemap3D.syncCampaign) {
    window.Battlemap3D.syncCampaign(state.activeCampaign);
  }
}

/* ==================== UI RENDERING ==================== */
function renderActiveCampaign() {
  const camp = state.activeCampaign;
  if (!camp) return;
  const bmap = camp.battlemap;
  const hero = camp.hero;
  const heroPortrait = hero.portrait || "/static/assets/portraits/hero_paladin.jpg";

  document.getElementById("activeCampaignSubtitle").textContent =
    `${camp.title} • ${bmap.biome_name} • Hero: ${hero.name} (Lvl ${hero.level} ${hero.class_name})`;

  // Selectors sync
  const qSel = document.getElementById("quickCampaignSelect");
  if (qSel && qSel.value !== camp.id) qSel.value = camp.id;
  const bSel = document.getElementById("biomeSelect");
  if (bSel && bSel.value !== bmap.biome_id) bSel.value = bmap.biome_id;

  // Map Header & Controls
  document.getElementById("mapBiomeTitle").textContent = `🏰 ${bmap.biome_name}`;
  const lastTurn = (camp.chronicle || [])[camp.chronicle.length - 1];
  const roomName = lastTurn ? lastTurn.room_name : bmap.rooms[0].name;
  document.getElementById("mapRoomSubtitle").textContent =
    `Room: ${roomName} • Revealed: ${(bmap.revealed || []).length}/${bmap.width * bmap.height} tiles • 3D Scale: 5 ft/tile`;
  document.getElementById("heroCoordPill").textContent =
    `Hero Mini @ (${bmap.hero_pos.x}, ${bmap.hero_pos.y}) • Vision: ${hero.vision_radius * 5} ft`;
  document.getElementById("toggleFogBtn").textContent = bmap.fog_of_war ? "🌫️ Fog: ON" : "☀️ Fog: OFF";

  const pngLink = document.getElementById("exportMapPngBtn");
  if (pngLink) pngLink.href = `/api/campaigns/${camp.id}/battlemap.png`;
  const mdLink = document.getElementById("downloadMdBtn");
  if (mdLink) mdLink.href = `/api/campaigns/${camp.id}/export.md`;
  const htmlLink = document.getElementById("downloadHtmlBtn");
  if (htmlLink) htmlLink.href = `/api/campaigns/${camp.id}/export.html`;

  // 4-Agent Telemetry Cards
  if (lastTurn && lastTurn.agents) {
    const ag = lastTurn.agents;
    if (ag.worldbuilder) {
      document.getElementById("worldAgentModeBadge").textContent = (ag.worldbuilder.provider || "offline").toUpperCase();
      document.getElementById("worldAgentSummary").textContent = ag.worldbuilder.summary || "";
    }
    if (ag.rules_lawyer) {
      document.getElementById("rulesAgentVerdictBadge").textContent = ag.rules_lawyer.verdict || "RESOLVED";
      document.getElementById("rulesAgentSummary").textContent = ag.rules_lawyer.summary || "";
    }
    if (ag.npc_actor) {
      document.getElementById("npcAgentDispBadge").textContent = ag.npc_actor.disposition || "ACTIVE";
      document.getElementById("npcAgentSummary").textContent = ag.npc_actor.summary || "";
    }
    if (ag.tactical_director) {
      document.getElementById("tacticalAgentRoundBadge").textContent = `ROUND ${ag.tactical_director.round || 1}`;
      document.getElementById("tacticalAgentSummary").textContent = ag.tactical_director.summary || "";
    }
  }

  // Hero Quick Vitals with Oil-Painted Portrait Medallion
  document.getElementById("deckHeroVitals").innerHTML = `
    <span class="vital-pill hero-portrait-pill">
      <img src="${esc(heroPortrait)}" alt="" class="vital-mini-avatar" />
      <strong>${esc(hero.name)}</strong>
    </span>
    <span class="vital-pill crimson-pill">❤️ HP ${hero.hp}/${hero.max_hp}</span>
    <span class="vital-pill cyan-pill">🔷 Mana ${hero.mana}/${hero.max_mana}</span>
    <span class="vital-pill gold-pill">🛡️ AC ${hero.ac}</span>
    <span class="vital-pill">🪙 ${hero.gold} gp</span>
    <span class="vital-pill">⭐ Lvl ${hero.level} (${hero.xp}/${hero.xp_next} XP)</span>
  `;

  // Tactical Initiative Tracker with Oil-Painted Hero & Monster Portraits
  const order = (camp.combat && camp.combat.order) || [];
  const initContainer = document.getElementById("initiativeOrderList");
  initContainer.innerHTML = order
    .map((c) => {
      const pct = Math.max(0, Math.min(100, Math.round((c.hp / Math.max(1, c.max_hp)) * 100)));
      const portraitUrl =
        c.portrait ||
        (c.side === "hero"
          ? heroPortrait
          : "/static/assets/portraits/monster_dragon.jpg");
      const badgeLabel = c.side === "hero" ? "HERO" : c.side === "ally" ? "ALLY" : "BOSS / FOE";
      return `
        <div class="init-card ${c.side === "hero" ? "hero-side" : "monster-side"} ${c.alive ? "" : "dead"}" data-unit-id="${esc(c.id)}" data-side="${esc(c.side)}">
          <div class="init-card-row">
            <img src="${esc(portraitUrl)}" alt="${esc(c.name)}" class="init-portrait-img" />
            <div class="init-card-body">
              <div class="init-top">
                <span class="init-unit-name">${esc(c.name)}</span>
                <span class="init-roll-badge">🎲 Init ${c.initiative}</span>
              </div>
              <div class="init-stats-row">
                <span>❤️ HP ${c.hp}/${c.max_hp}</span>
                <span>🛡️ AC ${c.ac}</span>
                <span class="init-side-tag">${badgeLabel}</span>
              </div>
              <div class="hp-bar-track">
                <div class="hp-bar-fill ${c.side === "monster" ? "monster" : ""}" style="width:${pct}%"></div>
              </div>
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  initContainer.querySelectorAll(".init-card").forEach((card) => {
    card.addEventListener("click", () => {
      const side = card.dataset.side;
      if (window.Battlemap3D) {
        window.Battlemap3D.setCameraMode(side === "hero" ? "hero" : "boss");
      }
    });
  });

  // Chronicle Feed (D&D Parchment Scroll Entries)
  const feedEl = document.getElementById("chronicleFeed");
  feedEl.innerHTML = (camp.chronicle || [])
    .slice()
    .reverse()
    .map((entry) => {
      const rl = (entry.agents && entry.agents.rules_lawyer) || {};
      const rollChip = rl.verdict
        ? `<div class="chronicle-roll-chip">⚖️ <strong>${esc(rl.verdict)}</strong> — ${esc(rl.summary || "")}</div>`
        : "";
      return `
        <div class="chronicle-entry">
          <div class="chronicle-entry-header">
            <span>📍 ${esc(entry.room_name || bmap.biome_name)}</span>
            <span>⏳ ${esc(entry.timestamp || "")}</span>
          </div>
          <div class="chronicle-action-tag">⚔️ ${esc(entry.player_action)}</div>
          <div class="chronicle-narrative-body">${formatSimpleMarkdown(entry.narrative)}</div>
          ${rollChip}
        </div>
      `;
    })
    .join("");

  // Quick Suggested Actions
  const suggEl = document.getElementById("suggestedActionsRow");
  suggEl.innerHTML = (camp.suggested_actions || [])
    .map(
      (s) =>
        `<button type="button" class="quick-action-chip" data-action="${esc(s.action)}" data-type="${esc(s.type)}">${esc(s.label)}</button>`
    )
    .join("");
  suggEl.querySelectorAll(".quick-action-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      submitGmAction(btn.dataset.action, btn.dataset.type);
    });
  });

  // Scene NPCs & Disposition Meters with Oil Portraits
  const dispTiers = ["Hostile", "Suspicious", "Neutral", "Friendly", "Sworn Ally"];
  const npcContainer = document.getElementById("npcCardsContainer");
  npcContainer.innerHTML = (camp.npcs || [])
    .map((npc) => {
      const npcPortrait = npc.portrait || "/static/assets/portraits/hero_wizard.jpg";
      const stepsHtml = dispTiers
        .map(
          (tier) =>
            `<div class="disp-step ${npc.disposition === tier ? "active-disp" : ""}">${esc(tier)}</div>`
        )
        .join("");
      const motiveText =
        npc.disposition === "Friendly" || npc.disposition === "Sworn Ally" || npc.secret_revealed
          ? esc(npc.secret_motive)
          : "🔒 Reach Friendly or Sworn Ally to unlock secret motive";
      const memoriesHtml = (npc.memory_log || [])
        .slice(-3)
        .map((m) => `<li>[${esc(m.time)}] ${esc(m.event)} → <strong>${esc(m.shift)}</strong></li>`)
        .join("");

      return `
        <div class="npc-card" data-npc-id="${esc(npc.id)}">
          <div class="npc-top">
            <div class="npc-identity">
              <img src="${esc(npcPortrait)}" alt="${esc(npc.name)}" class="npc-portrait-img" />
              <div>
                <div class="npc-name">${esc(npc.symbol || "🕯️")} ${esc(npc.name)} <span class="npc-score-tag">(${npc.disposition_score >= 0 ? "+" : ""}${npc.disposition_score})</span></div>
                <div class="npc-title">${esc(npc.title)} • Tile (${npc.x}, ${npc.y})</div>
              </div>
            </div>
            <div class="npc-interact-row">
              <button type="button" class="small-btn npc-act-btn" data-npc="${esc(npc.id)}" data-act="Swear an honorable oath and promise to aid ${esc(npc.name)}">🤝 Promise / Ally</button>
              <button type="button" class="small-btn gold-outline npc-act-btn" data-npc="${esc(npc.id)}" data-act="Offer 25 gold coin bribe to ${esc(npc.name)} for their secret help">🪙 Bribe 25 gp</button>
              <button type="button" class="small-btn crimson-outline npc-act-btn" data-npc="${esc(npc.id)}" data-act="Threaten and intimidate ${esc(npc.name)} into yielding">😠 Intimidate</button>
            </div>
          </div>
          <div class="disposition-track" aria-label="Disposition Meter">${stepsHtml}</div>
          <div class="npc-quirk">🗣️ <strong>Voice Quirk:</strong> ${esc(npc.voice_quirk)}</div>
          <div class="npc-motive">🗝️ <strong>Secret Motive:</strong> ${motiveText}</div>
          <ul class="npc-memory-list">${memoriesHtml}</ul>
        </div>
      `;
    })
    .join("");

  npcContainer.querySelectorAll(".npc-act-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      submitGmAction(btn.dataset.act, "roleplay", btn.dataset.npc);
    });
  });

  renderBattlemapCanvas();
  renderHeroView();
  renderRollHistory();
}

/* ==================== HERO BUILDER & INVENTORY VIEW ==================== */
function renderHeroView() {
  const camp = state.activeCampaign;
  if (!camp) return;
  const hero = camp.hero;

  // Presets Strip with Oil-Painted Portraits
  const strip = document.getElementById("heroPresetsStrip");
  strip.innerHTML = (state.catalog.heroes || [])
    .map((p) => {
      const port = p.portrait || "/static/assets/portraits/hero_paladin.jpg";
      return `
      <div class="preset-hero-card ${p.id === hero.id ? "active-preset" : ""}" data-preset-id="${esc(p.id)}">
        <img src="${esc(port)}" alt="${esc(p.name)}" class="preset-hero-portrait" />
        <div class="preset-hero-meta">
          <div class="preset-hero-name">${esc(p.token_symbol)} ${esc(p.name)}</div>
          <div class="preset-hero-class">${esc(p.ancestry)} • ${esc(p.class_name)}</div>
          <div class="preset-hero-stats">❤️ HP ${p.max_hp} | 🛡️ AC ${p.ac} | 🔷 Mana ${p.max_mana}</div>
        </div>
      </div>
    `;
    })
    .join("");

  strip.querySelectorAll(".preset-hero-card").forEach((card) => {
    card.addEventListener("click", async () => {
      const pid = card.dataset.presetId;
      const res = await apiFetch(`/api/campaigns/${camp.id}/hero/customize`, {
        method: "POST",
        body: { preset_id: pid },
      });
      state.activeCampaign = res.campaign;
      showHeroFeedback(`Switched active hero & 3D miniature to ${state.activeCampaign.hero.name}!`);
      renderActiveCampaign();
    });
  });

  const bannerEl = document.getElementById("heroActivePortraitBanner");
  if (bannerEl) {
    const heroPort = hero.portrait || "/static/assets/portraits/hero_paladin.jpg";
    bannerEl.innerHTML = `
      <img src="${esc(heroPort)}" alt="${esc(hero.name)}" class="hero-sheet-portrait-large" />
      <div class="hero-sheet-bio">
        <div class="hero-sheet-headline">${esc(hero.name)} <span class="version-pill">Lvl ${hero.level} ${esc(hero.class_name)}</span></div>
        <p class="hero-sheet-backstory">${esc(hero.backstory || "")}</p>
      </div>
    `;
  }

  document.getElementById("heroNameInput").value = hero.name || "";
  document.getElementById("heroAncestryInput").value = hero.ancestry || "";
  document.getElementById("heroClassInput").value = hero.class_name || "";

  // 6 Ability Score Boxes
  const abGrid = document.getElementById("heroAbilitiesGrid");
  abGrid.innerHTML = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    .map((ab) => {
      const score = hero.abilities[ab] ?? 10;
      const mod = hero.modifiers[ab] ?? 0;
      return `
        <div class="ability-box">
          <div class="ability-name">${ab}</div>
          <input type="number" class="ability-score-input" data-ability="${ab}" value="${score}" min="6" max="20" />
          <div class="ability-mod">${mod >= 0 ? `+${mod}` : mod}</div>
        </div>
      `;
    })
    .join("");

  document.getElementById("heroSkillsTags").innerHTML =
    `<span style="font-size:0.78rem;color:#cbd5e1;">Proficient Skills (+${hero.proficiency_bonus}): </span>` +
    (hero.proficient_skills || [])
      .map((s) => `<span class="version-pill" style="margin-right:5px;">${esc(s)}</span>`)
      .join("");

  // Inventory List
  const invEl = document.getElementById("heroInventoryList");
  invEl.innerHTML = (hero.inventory || [])
    .map((it) => {
      const actionLabel =
        it.type === "potion"
          ? `🧪 Drink (${it.qty || 1})`
          : it.equipped
          ? "✅ Equipped (Unequip)"
          : "🛡️ Equip";
      return `
        <div class="item-row">
          <div>
            <div style="font-weight:700;font-size:0.86rem;color:#fef3c7;">${esc(it.name)} ${it.equipped ? '<span class="version-pill">Equipped</span>' : ""}</div>
            <div style="font-size:0.75rem;color:#94a3b8;">${esc(it.desc || "")}</div>
          </div>
          <button type="button" class="small-btn item-action-btn" data-item-id="${esc(it.id)}">${actionLabel}</button>
        </div>
      `;
    })
    .join("");

  invEl.querySelectorAll(".item-action-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const res = await apiFetch(`/api/campaigns/${camp.id}/hero/item`, {
        method: "POST",
        body: { item_id: btn.dataset.itemId },
      });
      state.activeCampaign = res.campaign;
      showHeroFeedback(res.message);
      renderActiveCampaign();
    });
  });

  // Spells List
  const spellsEl = document.getElementById("heroSpellsList");
  spellsEl.innerHTML = (hero.spells || [])
    .map(
      (sp) => `
      <div class="spell-row">
        <div>
          <div style="font-weight:700;font-size:0.86rem;color:#38bdf8;">✨ ${esc(sp.name)} <span style="font-size:0.73rem;color:#fbbf24;">(${sp.cost_mana} Mana • ${sp.ability})</span></div>
          <div style="font-size:0.75rem;color:#94a3b8;">${esc(sp.desc)}</div>
        </div>
        <button type="button" class="small-btn gold-outline cast-spell-btn" data-spell-name="${esc(sp.name)}" data-vfx="${esc(sp.vfx || "fireball")}">🔥 Cast in 3D</button>
      </div>
    `
    )
    .join("");

  spellsEl.querySelectorAll(".cast-spell-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const spName = btn.dataset.spellName;
      switchView("deck");
      await submitGmAction(`Cast ${spName} in combat`, "spell");
    });
  });
}

function showHeroFeedback(msg) {
  const el = document.getElementById("heroActionFeedback");
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
}

/* ==================== DICE TRAY & PROBABILITY ODDS ==================== */
async function executePolyhedralRoll(forcedNatural = null) {
  const count = parseInt(document.getElementById("diceCountInput").value || "1", 10);
  const modifier = parseInt(document.getElementById("diceModInput").value || "0", 10);
  const dc = parseInt(document.getElementById("diceDcInput").value || "14", 10);
  const campId = state.activeCampaign ? state.activeCampaign.id : null;

  const token = document.getElementById("animatedDieToken");
  token.classList.add("rolling");
  setTimeout(() => token.classList.remove("rolling"), 380);

  const res = await apiFetch("/api/dice/roll", {
    method: "POST",
    body: {
      sides: state.selectedSides,
      count,
      modifier,
      mode: state.diceMode,
      dc,
      campaign_id: campId,
      forced_natural: forcedNatural,
    },
  });

  const roll = res.roll;
  token.textContent = roll.total;

  if (roll.is_nat20) {
    playCritFanfareSfx();
  } else if (roll.is_nat1) {
    playFumbleSfx();
  } else {
    playDiceClatterSfx();
  }

  if (window.Battlemap3D) {
    window.Battlemap3D.trigger3DDiceRoll(roll.sides, roll.total, roll.is_nat20, roll.is_nat1);
  }

  const headEl = document.getElementById("diceResultHeadline");
  const subEl = document.getElementById("diceResultBreakdown");

  if (roll.is_nat20) {
    headEl.textContent = `🌟 NATURAL 20! CRITICAL HIT! Total ${roll.total} vs DC ${roll.dc}`;
  } else if (roll.is_nat1) {
    headEl.textContent = `💀 NATURAL 1! CRITICAL FUMBLE! Total ${roll.total} vs DC ${roll.dc}`;
  } else {
    headEl.textContent = `${roll.formula} → Total ${roll.total} (${roll.success ? "PASSED" : "MISSED"} DC ${roll.dc})`;
  }

  const discStr = roll.discarded && roll.discarded.length ? ` | Discarded: [${roll.discarded.join(", ")}]` : "";
  subEl.textContent = `Natural Roll: [${roll.rolls.join(", ")}]${discStr} | Modifier: ${roll.modifier >= 0 ? "+" : ""}${roll.modifier}`;

  if (state.activeCampaign) {
    state.activeCampaign.dice_history = [roll, ...(state.activeCampaign.dice_history || [])].slice(0, 40);
    renderRollHistory();
  }
  renderProbabilityStats(roll.stats);
  return roll;
}

async function refreshDiceStats() {
  const count = parseInt(document.getElementById("diceCountInput").value || "1", 10);
  const modifier = parseInt(document.getElementById("diceModInput").value || "0", 10);
  const dc = parseInt(document.getElementById("diceDcInput").value || "14", 10);
  const res = await apiFetch(
    `/api/dice/stats?sides=${state.selectedSides}&count=${count}&modifier=${modifier}&mode=${state.diceMode}&dc=${dc}`
  );
  renderProbabilityStats(res.stats);
}

function renderProbabilityStats(stats) {
  if (!stats) return;
  document.getElementById("probMetricsGrid").innerHTML = `
    <div class="metric-tile"><div class="metric-val">${stats.expected_value}</div><div class="metric-lbl">Expected Value</div></div>
    <div class="metric-tile"><div class="metric-val">±${stats.std_dev}</div><div class="metric-lbl">Std Deviation</div></div>
    <div class="metric-tile"><div class="metric-val">${stats.min_total}–${stats.max_total}</div><div class="metric-lbl">Min / Max</div></div>
    <div class="metric-tile"><div class="metric-val">${stats.pass_probability_pct ?? "—"}%</div><div class="metric-lbl">Pass vs DC ${stats.dc ?? 14}</div></div>
    <div class="metric-tile"><div class="metric-val">${stats.crit_chance_pct}%</div><div class="metric-lbl">Nat 20 Crit %</div></div>
  `;

  const hist = stats.histogram || [];
  const maxP = Math.max(0.01, ...hist.map((b) => b.probability));
  document.getElementById("probHistogram").innerHTML = hist
    .map((b) => {
      const hPct = Math.max(8, Math.round((b.probability / maxP) * 100));
      return `
        <div class="hist-bar-col" title="Value ${b.value}: ${(b.probability * 100).toFixed(1)}%">
          <div class="hist-bar" style="height:${hPct}%"></div>
          <span class="hist-lbl">${b.value}</span>
        </div>
      `;
    })
    .join("");
}

function renderRollHistory() {
  const listEl = document.getElementById("rollHistoryList");
  if (!listEl || !state.activeCampaign) return;
  const rolls = state.activeCampaign.dice_history || [];
  listEl.innerHTML = rolls
    .map((r) => {
      const badge = r.is_nat20
        ? '<span class="agent-status-badge gold">🌟 NAT 20</span>'
        : r.is_nat1
        ? '<span class="agent-status-badge crimson">💀 NAT 1</span>'
        : r.success === true
        ? '<span class="agent-status-badge">PASS</span>'
        : r.success === false
        ? '<span class="agent-status-badge crimson">FAIL</span>'
        : "";
      return `
        <div class="roll-row">
          <span><strong>${esc(r.formula)}</strong> — ${esc(r.label || "")}</span>
          <span>Nat ${r.natural} → <strong>${r.total}</strong> ${badge}</span>
        </div>
      `;
    })
    .join("");
}

/* ==================== CAMPAIGN VAULT & EXPORT ==================== */
function renderCampaignsVault() {
  const qSel = document.getElementById("quickCampaignSelect");
  qSel.innerHTML = state.campaigns
    .map((c) => `<option value="${esc(c.id)}">🏰 ${esc(c.title)} (${esc(c.hero_name)})</option>`)
    .join("");
  if (state.activeCampaign) qSel.value = state.activeCampaign.id;

  const vaultEl = document.getElementById("campaignsVaultGrid");
  vaultEl.innerHTML = state.campaigns
    .map(
      (c) => `
      <div class="vault-camp-card">
        <div>
          <div style="font-weight:800;color:#fef08a;">${esc(c.title)}</div>
          <div style="font-size:0.76rem;color:#38bdf8;">${esc(c.biome_name)} • ${esc(c.hero_name)} (Lvl ${c.hero_level}) • ${c.turns_count} turns</div>
          <div style="font-size:0.74rem;color:#94a3b8;">${esc(c.synopsis || "")}</div>
        </div>
        <div style="display:flex;gap:6px;">
          <button type="button" class="primary-btn load-camp-btn" data-id="${esc(c.id)}">📂 Load</button>
          <button type="button" class="small-btn reset-camp-btn" data-id="${esc(c.id)}">🔄 Reset</button>
        </div>
      </div>
    `
    )
    .join("");

  vaultEl.querySelectorAll(".load-camp-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await loadCampaignById(btn.dataset.id);
      switchView("deck");
    });
  });
  vaultEl.querySelectorAll(".reset-camp-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const res = await apiFetch(`/api/campaigns/${btn.dataset.id}/reset`, { method: "POST" });
      state.activeCampaign = res.campaign;
      await refreshCampaignList();
      renderActiveCampaign();
    });
  });
}

async function refreshChronicleExportPreview() {
  if (!state.activeCampaign) return;
  const resp = await fetch(`/api/campaigns/${state.activeCampaign.id}/export.md`);
  const mdText = await resp.text();
  document.getElementById("chronicleMarkdownPreview").textContent = mdText;
}

/* ==================== CORE ACTIONS ==================== */
async function loadCampaignById(campaignId) {
  const res = await apiFetch(`/api/campaigns/${campaignId}`);
  state.activeCampaign = res.campaign;
  renderActiveCampaign();
}

async function refreshCampaignList() {
  const res = await apiFetch("/api/campaigns");
  state.campaigns = res.campaigns || [];
  renderCampaignsVault();
}

async function submitGmAction(actionText, actionType = "roleplay", targetNpcId = null) {
  if (!state.activeCampaign || !actionText.trim()) return;
  const diceMode = document.getElementById("deckDiceModeSelect").value || "normal";
  const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/action`, {
    method: "POST",
    body: {
      action_text: actionText.trim(),
      action_type: actionType,
      dice_mode: diceMode,
      target_npc_id: targetNpcId,
    },
  });
  state.activeCampaign = res.campaign;
  const roll = res.turn?.agents?.rules_lawyer?.roll;
  if (roll?.is_nat20) playCritFanfareSfx();
  else if (roll?.is_nat1) playFumbleSfx();
  else playDiceClatterSfx();

  // Trigger matching 3D VFX on the battlemap!
  if (window.Battlemap3D) {
    const lower = actionText.toLowerCase();
    if (actionType === "spell" || lower.includes("fireball") || lower.includes("smite") || lower.includes("attack")) {
      if (lower.includes("lightning") || lower.includes("bolt") || lower.includes("arc")) {
        window.Battlemap3D.triggerChainLightningVFX();
      } else if (lower.includes("heal") || lower.includes("rewind") || lower.includes("hands")) {
        window.Battlemap3D.triggerDivineHealVFX();
      } else {
        window.Battlemap3D.triggerFireballVFX();
      }
      playSpellBoomSfx();
    } else if (roll) {
      window.Battlemap3D.trigger3DDiceRoll(20, roll.total, roll.is_nat20, roll.is_nat1);
    }
  }

  renderActiveCampaign();
}

async function moveHeroByDelta(dx, dy) {
  if (!state.activeCampaign) return;
  const pos = state.activeCampaign.battlemap.hero_pos;
  await moveHeroToTile(pos.x + dx, pos.y + dy);
}

async function moveHeroToTile(tx, ty) {
  if (!state.activeCampaign) return;
  try {
    const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/move`, {
      method: "POST",
      body: { x: tx, y: ty },
    });
    state.activeCampaign = res.campaign;
    playDiceClatterSfx();
    renderActiveCampaign();
  } catch (err) {
    document.getElementById("hoverRangePill").textContent = `Blocked stone wall/pillar @ (${tx}, ${ty})`;
  }
}

window.moveHeroToTile = moveHeroToTile;

/* ==================== INITIALIZATION ==================== */
async function initApp() {
  if (window.Battlemap3D) {
    window.Battlemap3D.init();
  }

  const [catRes, campRes] = await Promise.all([apiFetch("/api/catalog"), apiFetch("/api/campaigns")]);
  state.catalog = catRes;
  state.campaigns = campRes.campaigns || [];

  // Populate Biome & Hero selects
  const biomeOptionsHtml = state.catalog.biomes
    .map((b) => `<option value="${esc(b.id)}">🗺️ ${esc(b.name)}</option>`)
    .join("");
  document.getElementById("biomeSelect").innerHTML = biomeOptionsHtml;
  document.getElementById("newCampBiome").innerHTML = biomeOptionsHtml;

  document.getElementById("newCampHero").innerHTML = state.catalog.heroes
    .map((h) => `<option value="${esc(h.id)}">${esc(h.token_symbol)} ${esc(h.name)} (${esc(h.class_name)})</option>`)
    .join("");

  // Settings sync
  const cfg = state.catalog.settings || {};
  document.getElementById("headerProviderBadge").textContent =
    `3D WebGL • 4-Agent GM (${(cfg.effective_provider || "offline").toUpperCase()})`;
  document.getElementById("settingsProvider").value = cfg.provider || "auto";
  document.getElementById("settingsOllamaUrl").value = cfg.ollama_url || "http://127.0.0.1:11434";
  document.getElementById("settingsOllamaModel").value = cfg.ollama_model || "llama3.2:latest";
  document.getElementById("settingsOpenaiModel").value = cfg.openai_model || "gpt-4o-mini";
  document.getElementById("settingsDiagnosticsBox").innerHTML = `
    <div><strong>Active Engine Provider:</strong> <code>${esc(cfg.effective_provider)}</code> (${esc(cfg.effective_model)})</div>
    <div><strong>3D Graphics Renderer:</strong> <code>Three.js WebGLRenderer (Shadows + Dynamic PointLights + Particle VFX)</code></div>
    <div><strong>Biomes Loaded:</strong> ${state.catalog.biomes.length} procedural 3D multi-room worlds</div>
    <div><strong>Playable Campaigns Ready:</strong> ${state.campaigns.length} campaigns</div>
  `;

  renderCampaignsVault();

  if (state.campaigns.length > 0) {
    await loadCampaignById(state.campaigns[0].id);
  }

  bindEvents();
  await refreshDiceStats();
}

function bindEvents() {
  // Navigation Tabs
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });

  // Topbar Campaign Switcher
  document.getElementById("quickCampaignSelect").addEventListener("change", (e) => {
    loadCampaignById(e.target.value);
  });

  // Ambient Soundscape button
  document.getElementById("ambientAudioBtn").addEventListener("click", toggleAmbientSoundscape);

  // Biome Switcher
  document.getElementById("biomeSelect").addEventListener("change", async (e) => {
    if (!state.activeCampaign) return;
    const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/biome`, {
      method: "POST",
      body: { biome_id: e.target.value },
    });
    state.activeCampaign = res.campaign;
    renderActiveCampaign();
  });

  // Fog-of-War Controls
  document.getElementById("toggleFogBtn").addEventListener("click", async () => {
    if (!state.activeCampaign) return;
    const nextFog = !state.activeCampaign.battlemap.fog_of_war;
    const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/fog`, {
      method: "POST",
      body: { fog_of_war: nextFog },
    });
    state.activeCampaign = res.campaign;
    renderActiveCampaign();
  });

  document.getElementById("revealAllFogBtn").addEventListener("click", async () => {
    if (!state.activeCampaign) return;
    const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/fog`, {
      method: "POST",
      body: { reveal_all: true },
    });
    state.activeCampaign = res.campaign;
    renderActiveCampaign();
  });

  // 3D Camera Mode Buttons
  document.querySelectorAll("[data-cam]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-cam]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      if (window.Battlemap3D) {
        window.Battlemap3D.setCameraMode(btn.dataset.cam);
      }
    });
  });

  // 3D Spell & Dice VFX Toolbar Buttons
  const fbBtn = document.getElementById("vfxFireballBtn");
  if (fbBtn) {
    fbBtn.addEventListener("click", () => {
      playSpellBoomSfx();
      if (window.Battlemap3D) window.Battlemap3D.triggerFireballVFX();
    });
  }

  const ltBtn = document.getElementById("vfxLightningBtn");
  if (ltBtn) {
    ltBtn.addEventListener("click", () => {
      playSpellBoomSfx();
      if (window.Battlemap3D) window.Battlemap3D.triggerChainLightningVFX();
    });
  }

  const hlBtn = document.getElementById("vfxHealBtn");
  if (hlBtn) {
    hlBtn.addEventListener("click", () => {
      playCritFanfareSfx();
      if (window.Battlemap3D) window.Battlemap3D.triggerDivineHealVFX();
    });
  }

  const dcBtn = document.getElementById("vfxDiceBtn");
  if (dcBtn) {
    dcBtn.addEventListener("click", () => {
      playDiceClatterSfx();
      if (window.Battlemap3D) window.Battlemap3D.trigger3DDiceRoll(20, 20, true, false);
    });
  }

  // D-Pad Movement Buttons
  document.querySelectorAll(".dpad-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      moveHeroByDelta(parseInt(btn.dataset.dx, 10), parseInt(btn.dataset.dy, 10));
    });
  });

  // Keyboard WASD / Arrow Keys when not typing in an input
  window.addEventListener("keydown", (e) => {
    if (state.activeView !== "deck") return;
    const tag = (document.activeElement && document.activeElement.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === "ArrowUp" || e.key === "w" || e.key === "W") {
      e.preventDefault();
      moveHeroByDelta(0, -1);
    } else if (e.key === "ArrowDown" || e.key === "s" || e.key === "S") {
      e.preventDefault();
      moveHeroByDelta(0, 1);
    } else if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") {
      e.preventDefault();
      moveHeroByDelta(-1, 0);
    } else if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") {
      e.preventDefault();
      moveHeroByDelta(1, 0);
    }
  });

  // Player Action Composer Form
  document.getElementById("gmActionForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("actionInput");
    const typeSel = document.getElementById("actionTypeSelect");
    const txt = input.value.trim();
    if (!txt) return;
    input.value = "";
    await submitGmAction(txt, typeSel.value);
  });

  // Polyhedral Dice Tray Buttons
  document.querySelectorAll(".poly-die-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".poly-die-btn").forEach((b) => b.classList.remove("active-die"));
      btn.classList.add("active-die");
      state.selectedSides = parseInt(btn.dataset.sides, 10);
      await executePolyhedralRoll();
    });
  });

  document.querySelectorAll("#diceModeGroup .mode-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#diceModeGroup .mode-toggle-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.diceMode = btn.dataset.mode;
      refreshDiceStats();
    });
  });

  document.getElementById("rollSelectedDieBtn").addEventListener("click", () => executePolyhedralRoll());
  document.getElementById("forceNat20Btn").addEventListener("click", () => {
    state.selectedSides = 20;
    executePolyhedralRoll(20);
  });
  document.getElementById("forceNat1Btn").addEventListener("click", () => {
    state.selectedSides = 20;
    executePolyhedralRoll(1);
  });

  ["diceCountInput", "diceModInput", "diceDcInput"].forEach((id) => {
    document.getElementById(id).addEventListener("change", refreshDiceStats);
  });

  // Hero Sheet Actions
  document.getElementById("heroRestBtn").addEventListener("click", async () => {
    if (!state.activeCampaign) return;
    const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/hero/progress`, {
      method: "POST",
      body: { action: "rest" },
    });
    state.activeCampaign = res.campaign;
    showHeroFeedback(res.message);
    if (window.Battlemap3D) window.Battlemap3D.triggerDivineHealVFX();
    renderActiveCampaign();
  });

  document.getElementById("heroGrantXpBtn").addEventListener("click", async () => {
    if (!state.activeCampaign) return;
    const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/hero/progress`, {
      method: "POST",
      body: { action: "xp", xp_amount: 900 },
    });
    state.activeCampaign = res.campaign;
    showHeroFeedback(res.message);
    playCritFanfareSfx();
    renderActiveCampaign();
  });

  document.getElementById("saveHeroCustomBtn").addEventListener("click", async () => {
    if (!state.activeCampaign) return;
    const abilities = {};
    document.querySelectorAll(".ability-score-input").forEach((inp) => {
      abilities[inp.dataset.ability] = parseInt(inp.value || "10", 10);
    });
    const res = await apiFetch(`/api/campaigns/${state.activeCampaign.id}/hero/customize`, {
      method: "POST",
      body: {
        name: document.getElementById("heroNameInput").value.trim(),
        ancestry: document.getElementById("heroAncestryInput").value.trim(),
        class_name: document.getElementById("heroClassInput").value.trim(),
        abilities,
      },
    });
    state.activeCampaign = res.campaign;
    showHeroFeedback(`Saved custom character sheet for ${state.activeCampaign.hero.name}!`);
    renderActiveCampaign();
  });

  // New Campaign Form
  document.getElementById("newCampaignForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("newCampTitle").value.trim();
    const biomeId = document.getElementById("newCampBiome").value;
    const heroId = document.getElementById("newCampHero").value;
    const res = await apiFetch("/api/campaigns", {
      method: "POST",
      body: { title, biome_id: biomeId, hero_preset_id: heroId },
    });
    state.activeCampaign = res.campaign;
    await refreshCampaignList();
    renderActiveCampaign();
    await refreshChronicleExportPreview();
  });

  // Settings Form
  document.getElementById("settingsForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await apiFetch("/api/settings", {
      method: "POST",
      body: {
        provider: document.getElementById("settingsProvider").value,
        ollama_url: document.getElementById("settingsOllamaUrl").value.trim(),
        ollama_model: document.getElementById("settingsOllamaModel").value.trim(),
        openai_model: document.getElementById("settingsOpenaiModel").value.trim(),
      },
    });
    const cfg = res.settings;
    document.getElementById("headerProviderBadge").textContent =
      `3D WebGL • 4-Agent GM (${(cfg.effective_provider || "offline").toUpperCase()})`;
    const badge = document.getElementById("settingsSavedBadge");
    badge.hidden = false;
    setTimeout(() => {
      badge.hidden = true;
    }, 2200);
  });

  // Sound SFX Test Buttons
  document.getElementById("testDiceSoundBtn").addEventListener("click", playDiceClatterSfx);
  document.getElementById("testCritSoundBtn").addEventListener("click", playCritFanfareSfx);
  document.getElementById("testFumbleSoundBtn").addEventListener("click", playFumbleSfx);
}

window.addEventListener("DOMContentLoaded", () => {
  initApp().catch((err) => {
    console.error("Failed to initialize Dungeon Master OS:", err);
  });
});
