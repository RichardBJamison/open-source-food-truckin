/* OSFT v1.1 — first run that unfolds like OSBW setup (welcome + optional AI → your truck → sections →
   Pass 1 walk section by section → review & approve map → Pass 2 first count → optional PIN lock),
   Settings › Sections, Settings › AI, and invoice upload with optional AI reading.
   AI only ever PROPOSES: nothing is saved until the user presses a save button. */
(function () {
  "use strict";
  const O = () => window.OSFT;
  const V = () => window.OSFT_V1;
  const t = (k) => O().t(k);
  const esc = (s) => O().esc(s);
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const api = (p, o) => O().api(p, o);
  const post = (p, b) => api(p, { method: "POST", body: JSON.stringify(b || {}) });
  const put = (p, b) => api(p, { method: "PUT", body: JSON.stringify(b || {}) });
  const card = (h, c) => V().card(h, c);
  const errBox = (id) => V().errBox(id);
  const okBox = (id) => V().okBox(id);
  const guard = (id, fn) => V().guard(id, fn);
  const flash = (id, m) => V().flash(id, m);
  const opt = (v, l, s) => V().opt(v, l, s);
  const es = () => O().locale === "es";

  async function upload(path, form) {
    const r = await fetch(path, { method: "POST", body: form, credentials: "same-origin" });
    let d = {};
    try { d = await r.json(); } catch (_) { d = {}; }
    if (!r.ok || d.ok === false) {
      if (r.status === 401 && O().onLoginRequired) O().onLoginRequired();
      throw new Error(d.error || `HTTP ${r.status}`);
    }
    return d;
  }

  /* ---------- shared state ---------- */
  let ob = null;
  let aiInfo = null;
  let secs = [];
  let suggestions = [];
  let walkIdx = 0;
  let countIdx = 0;
  async function loadAI() {
    try {
      aiInfo = await api("/api/ai");
      if (Array.isArray(aiInfo.presets)) aiInfo.presets = Object.fromEntries(aiInfo.presets.map((p) => [p.key, p]));
    } catch (_) { aiInfo = { ai: { enabled: false }, presets: {} }; } return aiInfo; }
  const aiOn = () => !!(aiInfo && aiInfo.ai && aiInfo.ai.enabled);
  async function loadSections() {
    const r = await api("/api/sections");
    secs = r.sections; suggestions = r.suggestions || [];
    await O().syncZones();
    return r;
  }
  const secName = (s) => O().zoneName(s.key);

  /* ---------- Sections editor (onboarding Step 2 + Settings › Sections) ---------- */
  function sectionsEditor(root, { onSaved, saveLabel, extraButtons = "" }) {
    let rows = secs.map((s) => ({ key: s.key, name: secName(s), count: s.count || 0 }));
    const draw = () => {
      const used = new Set(rows.map((r) => r.name.toLowerCase()));
      root.innerHTML = `${errBox("sec-error")}${okBox("sec-ok")}
        <ol class="sec-list" id="sec-list">${rows.map((r, i) => `<li class="sec-row">
          <span class="sec-num">${i + 1}</span>
          <label class="sr" for="sec-name-${i}">${t("sec_name")}</label>
          <input id="sec-name-${i}" data-sec-name="${i}" value="${esc(r.name)}" maxlength="40" />
          <span class="muted sec-count">${r.count ? `${r.count} ${t("sec_products")}` : ""}</span>
          <button type="button" class="btn btn-sm btn-ghost" data-sec-up="${i}" aria-label="${t("sec_up")}" ${i === 0 ? "disabled" : ""}>↑</button>
          <button type="button" class="btn btn-sm btn-ghost" data-sec-down="${i}" aria-label="${t("sec_down")}" ${i === rows.length - 1 ? "disabled" : ""}>↓</button>
          <button type="button" class="btn btn-sm btn-ghost" data-sec-del="${i}" aria-label="${t("sec_delete")}" ${rows.length === 1 ? "disabled" : ""}>✕</button>
        </li>`).join("")}</ol>
        <div class="row sec-add"><label class="sr" for="sec-new">${t("sec_add_label")}</label>
          <input id="sec-new" placeholder="${esc(t("sec_add_ph"))}" maxlength="40" />
          <button type="button" class="btn" id="sec-add">+ ${t("sec_add")}</button></div>
        <p class="muted" style="margin:.75rem 0 .35rem">${t("sec_suggest")}</p>
        <div class="chips">${suggestions.filter((g) => !used.has((es() ? g.name_es : g.name).toLowerCase()) && !used.has(g.name.toLowerCase()))
          .map((g) => `<button type="button" class="chip" data-sec-sugg="${esc(es() ? g.name_es : g.name)}">+ ${esc(es() ? g.name_es : g.name)}</button>`).join("")}</div>
        <div id="sec-move"></div>
        <div class="row ob-actions"><button type="button" class="btn btn-primary" id="sec-save">${saveLabel}</button>${extraButtons}</div>`;
      $$("[data-sec-name]", root).forEach((el) => el.addEventListener("input", () => { rows[el.dataset.secName].name = el.value; }));
      $$("[data-sec-up]", root).forEach((b) => b.addEventListener("click", () => { const i = +b.dataset.secUp; [rows[i - 1], rows[i]] = [rows[i], rows[i - 1]]; draw(); }));
      $$("[data-sec-down]", root).forEach((b) => b.addEventListener("click", () => { const i = +b.dataset.secDown; [rows[i + 1], rows[i]] = [rows[i], rows[i + 1]]; draw(); }));
      $$("[data-sec-del]", root).forEach((b) => b.addEventListener("click", () => { rows.splice(+b.dataset.secDel, 1); draw(); }));
      const add = (name) => { name = (name || "").trim(); if (!name) return; rows.push({ key: null, name, count: 0 }); draw(); $("#sec-new", root).focus(); };
      $("#sec-add", root).addEventListener("click", () => add($("#sec-new", root).value));
      $("#sec-new", root).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); add(e.target.value); } });
      $$("[data-sec-sugg]", root).forEach((b) => b.addEventListener("click", () => add(b.dataset.secSugg)));
      $("#sec-save", root).addEventListener("click", () => save());
    };
    const save = (moveTo) => guard("sec-error", async () => {
      const body = { sections: rows.map((r) => (r.key ? { key: r.key, name: r.name.trim() } : { name: r.name.trim() })) };
      if (moveTo) body.move_to = moveTo;
      const res = await fetch("/api/sections", { method: "PUT", headers: { "Content-Type": "application/json" }, credentials: "same-origin", body: JSON.stringify(body) });
      const d = await res.json().catch(() => ({}));
      if (res.status === 409 && d.needs_move) {
        const keep = rows.filter((r) => r.key);
        if (!keep.length) throw new Error(d.error);
        $("#sec-move", root).innerHTML = `<div class="alert alert-warn">${esc(d.error)}
          <div class="row" style="margin-top:.5rem"><label for="sec-move-to">${t("sec_move_to")}</label>
          <select id="sec-move-to">${keep.map((r) => opt(r.key, r.name)).join("")}</select>
          <button type="button" class="btn btn-sm btn-primary" id="sec-move-go">${t("sec_move_go")}</button></div></div>`;
        $("#sec-move-go", root).addEventListener("click", () => save($("#sec-move-to", root).value));
        return;
      }
      if (!res.ok || d.ok === false) throw new Error(d.error || `HTTP ${res.status}`);
      await loadSections();
      rows = secs.map((s) => ({ key: s.key, name: secName(s), count: s.count || 0 }));
      draw();
      flash("sec-ok", t("saved"));
      if (onSaved) await onSaved();
    });
    draw();
  }

  async function renderSectionsView() {
    await loadSections();
    const root = $("#sections-root");
    root.innerHTML = card(`<h2>${t("tab_sections_title")}</h2><p class="muted">${t("sec_hint")}</p><div id="sec-ed"></div>`);
    sectionsEditor($("#sec-ed"), { saveLabel: t("btn_save") });
  }

  /* ---------- AI settings (Settings › AI and the welcome panel) ---------- */
  function presetName(k) { return t("ai_p_" + k); }
  async function renderAIView() {
    await loadAI();
    const a = aiInfo.ai, P = aiInfo.presets || {};
    const root = $("#ai-root");
    root.innerHTML = card(`<h2>${t("tab_ai_title")}</h2><p class="muted">${t("ai_settings_hint")}</p>
      ${errBox("ai-err")}${okBox("ai-okmsg")}
      <div class="ai-status ${a.enabled ? "on" : ""}" id="ai-status">${a.enabled ? "● " + t("ai_is_on") : "○ " + t("ai_is_off")}${a.last_test ? ` · ${t("ai_last_test")}: ${a.last_test.ok ? "✓" : "✗"} ${esc(O().fmtWhen(a.last_test.at))}` : ""}</div>
      <form id="ais-form" class="form-grid cols-2" novalidate>
        <div style="grid-column:1/-1"><label class="check"><input type="checkbox" id="ais-on" ${a.enabled ? "checked" : ""} /> <strong>${t("ai_switch")}</strong></label></div>
        <div><label for="ais-provider">${t("ai_provider")}</label><select id="ais-provider">${Object.keys(P).map((k) => opt(k, presetName(k), k === (a.provider || "openai"))).join("")}</select></div>
        <div><label for="ais-model">${t("ai_model")}</label><input id="ais-model" value="${esc(a.model || "")}" autocomplete="off" /></div>
        <div style="grid-column:1/-1"><label for="ais-url">${t("ai_endpoint")}</label><input id="ais-url" value="${esc(a.base_url || "")}" inputmode="url" autocomplete="off" /></div>
        <div style="grid-column:1/-1"><label for="ais-key">${t("ai_key")}</label>
          <input id="ais-key" type="password" autocomplete="off" placeholder="${a.has_key ? esc(t("ai_key_saved") + " ••••" + (a.key_hint || "")) : esc(t("ai_key_ph"))}" />
          <p class="muted small">${t("ai_key_note")}</p></div>
        <div class="row" style="grid-column:1/-1"><button type="submit" class="btn btn-primary">${t("btn_save")}</button>
          <button type="button" class="btn" id="ais-test">${t("ai_test")}</button>
          ${a.has_key ? `<button type="button" class="btn btn-ghost" id="ais-clear">${t("ai_clear")}</button>` : ""}</div>
      </form>
      <div id="ais-test-out"></div>
      <h3>${t("ai_uses_title")}</h3><ul class="ob-list"><li>${t("ai_use_1")}</li><li>${t("ai_use_2")}</li><li>${t("ai_use_3")}</li></ul>`);
    $("#ais-provider").addEventListener("change", (e) => {
      const p = P[e.target.value] || {};
      if (p.base_url !== undefined) $("#ais-url").value = p.base_url;
      if (p.model !== undefined) $("#ais-model").value = p.model;
    });
    const save = (extra = {}) => {
      const body = { enabled: $("#ais-on").checked, provider: $("#ais-provider").value, base_url: $("#ais-url").value.trim(), model: $("#ais-model").value.trim(), ...extra };
      const k = $("#ais-key").value.trim();
      if (k) body.api_key = k;
      return put("/api/ai/settings", body);
    };
    $("#ais-form").addEventListener("submit", (e) => { e.preventDefault(); guard("ai-err", async () => { await save(); await renderAIView(); flash("ai-okmsg", t("saved")); }); });
    $("#ais-test").addEventListener("click", () => guard("ai-err", async () => {
      $("#ais-test-out").innerHTML = `<p class="muted">${t("ai_testing")}</p>`;
      if ($("#ais-key").value.trim() || !aiInfo.ai.provider) await save();
      const r = await post("/api/ai/test");
      $("#ais-test-out").innerHTML = `<div class="alert alert-ok">✓ ${t("ai_test_ok")} ${esc(r.model || "")}</div>`;
    }).then((v) => { if (v === null) $("#ais-test-out").innerHTML = ""; }));
    const clr = $("#ais-clear");
    if (clr) clr.addEventListener("click", () => guard("ai-err", async () => { await put("/api/ai/settings", { clear_key: true, enabled: false }); await renderAIView(); }));
  }

  /* ---------- Onboarding ---------- */
  const STEPS = ["business", "sections", "walk", "reconcile", "review", "first_count", "account"];
  function stepper(ph) {
    const idx = STEPS.indexOf(ph);
    return `<ol class="ob-steps">${STEPS.map((p, i) => `<li class="${i < idx ? "done" : i === idx ? "on" : ""}">${t("ob11_step_" + p)}</li>`).join("")}</ol>`;
  }
  async function setPhase(phase) { ob = await put("/api/onboarding", { phase }); return renderOnboarding(); }
  function prime(info) { ob = info; }

  async function renderOnboarding(fresh) {
    document.body.classList.add("focus-mode");
    if (fresh || !ob) ob = await api("/api/onboarding");
    const root = $("#onboarding-root");
    const ph = ob.onboarding.phase;
    await loadAI();
    if (ph === "welcome") return obWelcome(root);
    if (ph === "done") return obDone(root);
    await loadSections();
    const head = `<p class="view-eyebrow ob-pass">${t(["walk", "sections", "reconcile", "review"].includes(ph) ? "ob11_pass1" : ph === "first_count" ? "ob11_pass2" : "ob11_getstarted")}</p>` + stepper(ph);
    if (ph === "business") return obBusiness(root, head);
    if (ph === "sections") return obSections(root, head);
    if (ph === "walk") return obWalk(root, head);
    if (ph === "reconcile") return obReconcile(root, head);
    if (ph === "review") return obReview(root, head);
    if (ph === "first_count") return obCount(root, head);
    if (ph === "account") return obAccount(root, head);
    return obDone(root);
  }

  function obWelcome(root) {
    const P = aiInfo.presets || {};
    root.innerHTML = card(`<div class="ob-welcome">
      <img src="/static/img/hero-1024.webp" alt="" class="ob-hero" />
      <p class="view-eyebrow">${t("ob_eyebrow")}</p>
      <h1>${t("ob11_welcome_title")}</h1>
      <p>${t("ob11_welcome_body")}</p></div>
      <div class="ob-passes">
        <div class="ob-pass-card"><h3>${t("ob11_pass1_title")}</h3><ol><li>${t("ob11_p1_1")}</li><li>${t("ob11_p1_2")}</li><li>${t("ob11_p1_3")}</li></ol></div>
        <div class="ob-pass-card"><h3>${t("ob11_pass2_title")}</h3><ol><li>${t("ob11_p2_1")}</li><li>${t("ob11_p2_2")}</li></ol></div>
      </div>
      <p class="muted">${t("ob11_tip")}</p>
      ${errBox("ob-error")}
      <details class="ob-ai" id="ob-ai" ${aiOn() ? "open" : ""}><summary><strong>✨ ${t("ob11_ai_title")}</strong> <span class="muted">${t("ob11_ai_optional")}</span></summary>
        <p class="muted">${t("ob11_ai_body")}</p>
        ${aiOn() ? `<div class="alert alert-ok">✓ ${t("ai_is_on")} — ${esc(presetName(aiInfo.ai.provider))}</div>` : `
        <div class="form-grid cols-2">
          <div><label for="ob-ai-provider">${t("ai_provider")}</label><select id="ob-ai-provider">${Object.keys(P).map((k) => opt(k, presetName(k), k === "openai")).join("")}</select></div>
          <div><label for="ob-ai-key">${t("ai_key")}</label><input id="ob-ai-key" type="password" autocomplete="off" placeholder="${esc(t("ai_key_ph"))}" /></div>
          <div id="ob-ai-urlbox" class="hidden"><label for="ob-ai-url">${t("ai_endpoint")}</label><input id="ob-ai-url" inputmode="url" /></div>
          <div id="ob-ai-modelbox" class="hidden"><label for="ob-ai-model">${t("ai_model")}</label><input id="ob-ai-model" autocomplete="off" /></div>
        </div>
        <p class="muted small">${t("ai_key_note")}</p>
        <button type="button" class="btn" id="ob-ai-connect">${t("ob11_ai_connect")}</button>
        <div id="ob-ai-out"></div>`}
      </details>
      <div class="row ob-actions">
        <button type="button" class="btn btn-primary" id="ob-start">${t("ob11_begin")}</button>
        <button type="button" class="btn" id="ob-sample">🌮 ${t("ob_sample")}</button>
      </div>
      <p class="muted">${t("ob_sample_hint")}</p>
      <label class="check"><input type="checkbox" id="ob-updates" /> ${t("ob_updates")}</label>`, "ob-card");
    const prov = $("#ob-ai-provider");
    if (prov) {
      const sync = () => { const p = prov.value; const show = p === "custom" || p === "ollama";
        $("#ob-ai-urlbox").classList.toggle("hidden", !show); $("#ob-ai-modelbox").classList.toggle("hidden", !show);
        $("#ob-ai-url").value = (P[p] || {}).base_url || ""; $("#ob-ai-model").value = (P[p] || {}).model || ""; };
      prov.addEventListener("change", sync); sync();
      $("#ob-ai-connect").addEventListener("click", () => guard("ob-error", async () => {
        const p = prov.value;
        $("#ob-ai-out").innerHTML = `<p class="muted">${t("ai_testing")}</p>`;
        await put("/api/ai/settings", { provider: p, base_url: $("#ob-ai-url").value.trim() || (P[p] || {}).base_url, model: $("#ob-ai-model").value.trim() || (P[p] || {}).model, api_key: $("#ob-ai-key").value.trim(), enabled: true });
        try {
          await post("/api/ai/test");
          await renderOnboarding();
        } catch (e) {
          await put("/api/ai/settings", { enabled: false }).catch(() => null);
          $("#ob-ai-out").innerHTML = `<div class="alert alert-warn">${esc(e.message)}<br>${t("ob11_ai_failed")}</div>`;
        }
      }).then(() => null));
    }
    $("#ob-start").addEventListener("click", () => guard("ob-error", async () => {
      if ($("#ob-updates").checked) await put("/api/business", { updates_opt_in: true }).catch(() => null);
      await setPhase("business");
    }));
    $("#ob-sample").addEventListener("click", () => guard("ob-error", async () => { await post("/api/onboarding/sample"); ob = null; V().finishOnboarding(); }));
  }

  function obBusiness(root, head) {
    const b = ob.business || {};
    const cyc = Number(b.cycle_days || 7);
    root.innerHTML = head + card(`<h2>${t("ob11_business_title")}</h2><p class="muted">${t("ob_business_hint")}</p>${errBox("ob-error")}
      <form id="ob-biz" class="form-grid cols-2" novalidate>
        <div style="grid-column:1/-1"><label for="ob-name">${t("label_business_name")}</label><input id="ob-name" required value="${esc(b.name || "")}" autocomplete="organization" /></div>
        <div style="grid-column:1/-1"><span class="label">${t("ob11_cycle")}</span><div class="row seg">
          <label class="check"><input type="radio" name="ob-cyc" value="7" ${cyc === 7 ? "checked" : ""}/> ${t("ob11_weekly")}</label>
          <label class="check"><input type="radio" name="ob-cyc" value="14" ${cyc === 14 ? "checked" : ""}/> ${t("ob11_biweekly")}</label>
          <label class="check"><input type="radio" name="ob-cyc" value="30" ${cyc === 30 ? "checked" : ""}/> ${t("ob11_monthly")}</label></div></div>
        <div><label for="ob-phone">${t("label_phone")}</label><input id="ob-phone" type="tel" value="${esc(b.phone || "")}" /></div>
        <div><label for="ob-email">${t("label_email")}</label><input id="ob-email" type="email" value="${esc(b.email || "")}" /></div>
        <div><label for="ob-tz">${t("label_timezone")}</label><input id="ob-tz" value="${esc(b.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "")}" /></div>
        <div class="row" style="grid-column:1/-1"><button type="submit" class="btn btn-primary">${t("btn_next")}</button>
        <button type="button" class="btn btn-ghost" id="ob-back">${t("btn_back")}</button></div>
      </form>`);
    $("#ob-back").addEventListener("click", () => setPhase("welcome"));
    $("#ob-biz").addEventListener("submit", (e) => { e.preventDefault(); guard("ob-error", async () => {
      const name = $("#ob-name").value.trim();
      if (!name) throw new Error(t("ob11_need_name"));
      const c = ($$("[name=ob-cyc]").find((r) => r.checked) || {}).value || 7;
      await put("/api/business", { name, phone: $("#ob-phone").value, email: $("#ob-email").value, cycle_days: c, timezone: $("#ob-tz").value });
      await put("/api/settings", { truck_name: name }).catch(() => null);
      $("#truck-label").textContent = name;
      await setPhase("sections");
    }); });
  }

  function obSections(root, head) {
    root.innerHTML = head + card(`<h2>${t("ob11_sections_title")}</h2><p>${t("ob11_sections_hint")}</p>
      <p class="muted">${t("ob11_sections_hint2")}</p>${errBox("ob-error")}<div id="ob-sec"></div>`);
    sectionsEditor($("#ob-sec"), {
      saveLabel: t("ob11_sections_go"),
      extraButtons: `<button type="button" class="btn btn-ghost" id="ob-sec-back">${t("btn_back")}</button>`,
      onSaved: async () => { walkIdx = 0; await setPhase("walk"); },
    });
    $("#ob-sec-back").addEventListener("click", () => setPhase("business"));
  }

  /* Pass 1 — walk one section at a time */
  let props = [];
  async function obWalk(root, head) {
    if (walkIdx >= secs.length) walkIdx = secs.length - 1;
    const s = secs[walkIdx];
    const items = ((await api("/api/items")).items || []).filter((i) => i.zone === s.key);
    root.innerHTML = head + card(`<div class="sec-progress">${secs.map((x, i) => `<button type="button" class="sec-pill ${i === walkIdx ? "on" : ""} ${x.count ? "has" : ""}" data-walk-go="${i}">${esc(secName(x))}${x.count ? ` · ${x.count}` : ""}</button>`).join("")}</div>
      <p class="muted">${t("ob11_section_of").replace("{n}", walkIdx + 1).replace("{total}", secs.length)}</p>
      <h2>${t("ob11_walk_title").replace("{section}", esc(secName(s)))}</h2>
      <p>${t("ob11_walk_hint")}</p>
      <p class="ob12-ask">📄 ${t("ob12_inv_ask")}</p>
      <details class="ob-howto"><summary>${t("ob11_howto")}</summary><ul class="ob-list"><li>${t("ob11_howto_1")}</li><li>${t("ob11_howto_2")}</li><li>${t("ob11_howto_3")}</li></ul>
        <p class="muted">${t("ob11_walk_example")}</p></details>
      ${errBox("ob-error")}
      ${V().micBlock("walk", "ob11_walk_ph")}
      <div class="inv-drop" id="inv-drop"></div>
      <div class="row">
        <button type="button" class="btn btn-primary" id="walk-check">${t("btn_check_walk")}</button>
        ${aiOn() ? `<button type="button" class="btn" id="walk-tidy">✨ ${t("ob11_ai_tidy")}</button>
        <label class="btn" for="walk-photo">📷 ${t("ob11_ai_photo")}</label><input id="walk-photo" type="file" accept="image/*" capture="environment" class="sr" />` : ""}
      </div>
      ${aiOn() ? "" : `<p class="muted small">${t("ob11_ai_hint_off")}</p>`}
      <div id="walk-review"></div>
      ${items.length ? `<h3>${t("ob11_in_section")}</h3><ul class="chips">${items.map((i) => `<li class="chip static">${esc(i.name)}${i.on_hand ? ` · ${O().fmtNum(i.on_hand)} ${esc(i.unit)}` : ""}</li>`).join("")}</ul>` : ""}
      <div class="row ob-actions">
        <button type="button" class="btn btn-ghost" id="walk-prev">← ${walkIdx === 0 ? t("ob11_edit_sections") : t("ob11_prev_section")}</button>
        <button type="button" class="btn ${items.length ? "btn-primary" : ""}" id="walk-next">${walkIdx < secs.length - 1 ? t("ob11_next_section") + " →" : t("ob11_to_review") + " →"}</button>
        <button type="button" class="btn btn-ghost" id="walk-starter">📚 ${t("btn_from_starter")}</button>
      </div>`) + `<div id="ob-starter"></div>`;
    V().attachMic($("#walk-mic"), $("#walk-text"), $("#walk-mic-status"));
    $$("[data-walk-go]").forEach((b) => b.addEventListener("click", () => { walkIdx = +b.dataset.walkGo; props = []; renderOnboarding(); }));
    $("#walk-prev").addEventListener("click", () => { props = []; if (walkIdx === 0) setPhase("sections"); else { walkIdx--; renderOnboarding(); } });
    $("#walk-next").addEventListener("click", () => { props = []; if (walkIdx < secs.length - 1) { walkIdx++; renderOnboarding(); } else setPhase("reconcile"); });
    drawInvoices();
    $("#walk-starter").addEventListener("click", () => V().renderStarter($("#ob-starter"), async () => renderOnboarding()));
    $("#walk-check").addEventListener("click", () => guard("ob-error", async () => {
      const r = await post("/api/voice/walk", { text: $("#walk-text").value, section: s.key });
      props = r.proposals.map((p) => ({ ...p, zone: s.key }));
      drawWalk(s);
    }));
    const fromAI = (list) => list.map((x) => ({ spoken: x.name, name: x.item_name || x.name, action: x.item_id ? "existing" : "new", item_id: x.item_id,
      unit: x.unit || "ea", category: x.category, on_hand: x.qty, zone: s.key, ai: true }));
    const tidy = $("#walk-tidy");
    if (tidy) tidy.addEventListener("click", () => guard("ob-error", async () => {
      tidy.disabled = true;
      try { const r = await post("/api/ai/tidy", { section: s.key, text: $("#walk-text").value }); props = fromAI(r.items); drawWalk(s); } finally { tidy.disabled = false; }
    }));
    const ph = $("#walk-photo");
    if (ph) ph.addEventListener("change", () => guard("ob-error", async () => {
      if (!ph.files[0]) return;
      const f = new FormData(); f.append("section", s.key); f.append("text", $("#walk-text").value); f.append("photo", ph.files[0]);
      $("#walk-review").innerHTML = `<p class="muted">${t("ob11_ai_reading")}</p>`;
      const r = await upload("/api/ai/shelf", f);
      props = fromAI(r.items); drawWalk(s); ph.value = "";
    }).then((v) => { if (v === null) $("#walk-review").innerHTML = ""; }));
  }
  function drawWalk(s) {
    const box = $("#walk-review");
    if (!props.length) { box.innerHTML = `<div class="alert alert-warn">${t("walk_nothing")}</div>`; return; }
    box.innerHTML = `<h3>${t("ob11_check_title").replace("{section}", esc(secName(s)))}</h3>
      ${props.some((p) => p.ai) ? `<p class="muted small">✨ ${t("ob11_ai_review_note")}</p>` : ""}
      <div class="table-wrap"><table class="walk-table"><thead><tr><th>${t("ob11_keep")}</th><th>${t("label_name")}</th><th>${t("label_unit")}</th><th>${t("ob11_qty_now")}</th></tr></thead><tbody>
      ${props.map((p, i) => `<tr><td><input type="checkbox" data-wp-keep="${i}" checked aria-label="${t("ob11_keep")}" /></td>
        <td><input data-wp-name="${i}" value="${esc(p.name)}" aria-label="${t("label_name")}" /><div class="muted small">${p.spoken && p.spoken !== p.name ? `“${esc(p.spoken)}” · ` : ""}${p.action === "existing" ? t("walk_existing") : t("ob11_new_product")}</div></td>
        <td><input data-wp-unit="${i}" value="${esc(p.unit || "ea")}" size="5" aria-label="${t("label_unit")}" /></td>
        <td><input type="number" min="0" step="any" inputmode="decimal" data-wp-oh="${i}" value="${p.on_hand ?? ""}" aria-label="${t("ob11_qty_now")}" /></td></tr>`).join("")}</tbody></table></div>
      <button type="button" class="btn btn-primary" id="walk-apply">${t("ob11_add_to").replace("{section}", esc(secName(s)))}</button>`;
    $("#walk-apply").addEventListener("click", () => guard("ob-error", async () => {
      const proposals = props.map((p, i) => ({ ...p, skip: !$(`[data-wp-keep="${i}"]`).checked, name: $(`[data-wp-name="${i}"]`).value.trim(), zone: s.key,
        unit: $(`[data-wp-unit="${i}"]`).value.trim() || "ea", on_hand: $(`[data-wp-oh="${i}"]`).value === "" ? null : Number($(`[data-wp-oh="${i}"]`).value) }));
      await post("/api/voice/walk/apply", { proposals });
      props = [];
      await renderOnboarding();
    }));
  }


  /* v1.2 — product invoices go in the same spot as the spoken products */
  async function drawInvoices() {
    const box = $("#inv-drop");
    if (!box) return;
    const r = await api("/api/setup/invoices");
    const inv = r.invoices || [];
    const nLines = inv.reduce((a, i) => a + (i.lines || []).length, 0);
    box.innerHTML = `<div class="inv-head"><strong>📄 ${t("ob12_inv_title")}</strong>
        <span class="muted small">${inv.length ? t("ob12_inv_count").replace("{n}", inv.length).replace("{lines}", nLines) : t("ob12_inv_none")}</span></div>
      <p class="muted small">${aiOn() ? t("ob12_inv_hint_ai") : t("ob12_inv_hint_off")}</p>
      <div class="row">
        <label class="btn" for="inv-files">📎 ${t("ob12_inv_upload")}</label>
        <input id="inv-files" type="file" multiple accept=".pdf,.csv,.txt,image/*" class="sr" />
        <label class="btn cam-only" for="inv-cam">📷 ${t("ob12_inv_camera")}</label>
        <input id="inv-cam" type="file" accept="image/*" capture="environment" class="sr" />
      </div>
      <div id="inv-status"></div>
      ${inv.length ? `<ul class="inv-list">${inv.map((i) => `<li><span>${esc(i.vendor || i.filename || t("ob12_typed"))}${i.invoice_no ? ` #${esc(i.invoice_no)}` : ""}
        · ${(i.lines || []).length} ${t("ob12_lines")} <span class="muted small">(${esc(t("ob12_src_" + i.source))})</span>
        ${i.note ? `<div class="small warn-text">${esc(i.note)}</div>` : ""}</span>
        <button type="button" class="btn btn-ghost btn-sm" data-inv-del="${i.id}" aria-label="${t("ob12_remove")}">✕</button></li>`).join("")}</ul>` : ""}
      <details class="inv-type" ${aiOn() ? "" : "open"}><summary>${t("ob12_type_title")}</summary>
        <div class="form-grid cols-2"><div><label for="inv-vendor">${t("ob12_vendor")}</label><input id="inv-vendor" /></div></div>
        <label for="inv-text" class="sr">${t("ob12_type_title")}</label>
        <textarea id="inv-text" rows="4" placeholder="${esc(t("ob12_type_ph"))}"></textarea>
        <button type="button" class="btn" id="inv-read">${t("ob12_type_read")}</button></details>`;
    const send = (files) => guard("ob-error", async () => {
      if (!files.length) return;
      const f = new FormData();
      [...files].forEach((x) => f.append("files", x));
      $("#inv-status").innerHTML = `<p class="muted">${aiOn() ? t("ob11_ai_reading") : t("ob12_reading")}</p>`;
      await upload("/api/setup/invoices", f);
      await drawInvoices();
    }).then((v) => { if (v === null && $("#inv-status")) $("#inv-status").innerHTML = ""; });
    $("#inv-files").addEventListener("change", (e) => send(e.target.files));
    $("#inv-cam").addEventListener("change", (e) => send(e.target.files));
    $("#inv-read").addEventListener("click", () => guard("ob-error", async () => {
      await post("/api/setup/invoices/text", { text: $("#inv-text").value, vendor: $("#inv-vendor").value });
      await drawInvoices();
    }));
    $$("[data-inv-del]").forEach((b) => b.addEventListener("click", () => guard("ob-error", async () => {
      await api(`/api/setup/invoices/${b.dataset.invDel}`, { method: "DELETE" }); await drawInvoices();
    })));
  }

  /* v1.2 — Pass 1 reconcile (OSBW setup step 3): spoken map × invoices, every gap shown before approve */
  let recon = null;
  const uState = {};   // unplaced choices survive live re-renders
  const uOver = {};    // unplaced edits (name/unit/pack/cost/vendor/count) sent with Confirm
  async function obReconcile(root, head, given) {
    recon = given || await api("/api/setup/reconcile");
    const P = recon.pending || { total: 0 };
    const allRows = recon.sections.flatMap((s) => s.items);
    const st = recon.stats, money = (v) => (v == null || v === "" ? "—" : "$" + Number(v).toFixed(2));
    const secOpts = (sel) => secs.map((x) => opt(x.key, secName(x), x.key === sel)).join("");
    const flag = (r) => r.flags.includes("no_cost") ? `<span class="flag">⚑ ${t("ob12_no_cost")}</span>`
      : r.flags.includes("unit_differs") ? `<span class="flag">⚑ ${t("ob13_unit_mismatch").replace("{a}", esc(r.unit)).replace("{b}", esc(r.invoice_unit))}</span>`
      : r.from_invoice ? `<span class="ok-text">✓ ${t("ob12_verified")}</span>` : `<span class="muted">${t("ob12_cost_entered")}</span>`;
    const report = recon.sections.map((s) => `<section class="rv-sec"><h3>${esc(s.name)} <span class="muted">${s.items.length} ${t("sec_products")}</span>
      <button type="button" class="btn btn-sm btn-ghost" data-rc-add="${esc(s.key)}">＋ ${t("ob13_add_here")}</button></h3>
      ${s.items.length ? `<div class="table-wrap"><table class="rc-table"><thead><tr><th>${t("label_item")}</th><th>${t("ob12_spoken")}</th><th>${t("ob12_on_invoice")}</th><th>${t("ob12_cost")}</th><th>${t("ob12_status")}</th><th class="sr">${t("ob13_edit")}</th></tr></thead><tbody>
      ${s.items.map((r) => `<tr class="rc-row ${r.edited.length || r.pending_new ? "rc-edited" : ""}" data-rc-row="${r.id}" tabindex="0"><td data-l="${esc(t("label_item"))}"><strong>${esc(r.name)}</strong>${r.pending_new ? ` <span class="pill">${t("ob13_new")}</span>` : r.edited.length ? ` <span class="pill">${t("ob13_edited")}</span>` : ""}${r.invoice_name && r.invoice_name.toLowerCase() !== r.name.toLowerCase() ? `<div class="muted small">“${esc(r.invoice_name)}”</div>` : ""}</td>
        <td data-l="${esc(t("ob12_spoken"))}">${r.spoken_qty ? `${O().fmtNum(r.spoken_qty)} ${esc(r.unit || "")}` : "—"}</td>
        <td data-l="${esc(t("ob12_on_invoice"))}">${r.from_invoice ? `${t("ob12_yes")}${r.vendor ? ` · ${esc(r.vendor)}` : ""}${r.pack ? ` · ${esc(r.pack)}` : ""}` : t("ob12_no")}</td>
        <td data-l="${esc(t("ob12_cost"))}">${money(r.cost)}${r.cost != null && r.invoice_unit ? ` / ${esc(r.invoice_unit)}` : ""}</td>
        <td data-l="${esc(t("ob12_status"))}">${flag(r)}</td>
        <td class="rc-edit-cell"><button type="button" class="btn btn-sm" data-rc-edit="${r.id}" aria-label="${esc(t("ob13_edit"))} ${esc(r.name)}">✎ <span class="rc-edit-word">${t("ob13_edit")}</span></button></td></tr>`).join("")}</tbody></table></div>` : `<p class="muted">${t("ob11_empty_section")}</p>`}</section>`).join("");
    const un = recon.unplaced;
    const unplaced = un.length ? `<section class="rc-unplaced" id="rc-unplaced"><h3>${t("ob12_unplaced_title").replace("{n}", un.length)}</h3>
      <p class="muted">${t("ob12_unplaced_hint")}</p>
      <div class="rc-bulk row"><label class="check"><input type="checkbox" id="rc-all" /> ${t("ob12_select_all")}</label>
        <select id="rc-bulk-sec" aria-label="${t("ob12_bulk_section")}">${secOpts()}</select>
        <button type="button" class="btn btn-sm" id="rc-bulk-put">${t("ob12_bulk_put")}</button>
        <button type="button" class="btn btn-sm" id="rc-bulk-comm">${t("ob12_bulk_comm")}</button>
        <button type="button" class="btn btn-sm" id="rc-bulk-ns">${t("ob12_bulk_ns")}</button>
        <button type="button" class="btn btn-sm btn-ghost" id="rc-bulk-skip">${t("ob12_bulk_skip")}</button></div>
      <ul class="rc-list">${un.map((g, i) => `<li class="rc-item" data-rc="${i}">
        <label class="check"><input type="checkbox" data-rc-pick="${i}" aria-label="${esc(g.name)}" /></label>
        <div class="rc-what"><strong>“${esc(g.name)}”</strong> <button type="button" class="btn btn-sm btn-ghost" data-rc-uedit="${i}" aria-label="${esc(t("ob13_edit"))}">✎ ${t("ob13_edit")}</button>${uOver[g.key] ? ` <span class="pill">${t("ob13_edited")}</span>` : ""} <span class="muted small">${[g.qty != null ? `${O().fmtNum(g.qty)} ${esc(g.unit || "")}` : "", g.unit_cost != null ? money(g.unit_cost) : "", g.vendors.join(", ")].filter(Boolean).join(" · ")}</span>
          <div class="muted small">${t("ob12_not_on_map")}${g.maybe ? ` ${t("ob12_maybe").replace("{name}", esc(g.maybe.name))}` : ""}</div></div>
        <div class="rc-do">
          <select data-rc-act="${i}" aria-label="${t("ob12_what_do")}">
            ${opt("section", t("ob12_act_section"), true)}${opt("new_section", t("ob12_act_new"))}${g.maybe ? opt("same_as", t("ob12_act_same").replace("{name}", g.maybe.name)) : ""}
            ${opt("commissary", t("ob12_act_comm"))}${opt("not_stocked", t("ob12_act_ns"))}${opt("skip", t("ob12_act_skip"))}</select>
          <select data-rc-sec="${i}" aria-label="${t("label_zone")}"><option value="">${t("ob12_pick_section")}</option>${secOpts(g.suggest)}</select>
          <input data-rc-new="${i}" class="hidden" placeholder="${esc(t("ob12_new_ph"))}" aria-label="${t("ob12_act_new")}" />
          <input data-rc-name="${i}" value="${esc((uOver[g.key] || {}).name || g.name)}" aria-label="${t("label_name")}" />
        </div></li>`).join("")}</ul></section>` : "";
    const noCost = recon.sections.flatMap((s) => s.items.filter((r) => r.flags.includes("no_cost")).map((r) => ({ ...r, sec: s.name })));
    root.innerHTML = head + card(`<h2>${t("ob12_title")}</h2><p class="muted">${t("ob12_lead")}</p>${errBox("ob-error")}
      <div class="stat-row rc-stats">
        <div><b>${st.sections}</b><span>${t("ob12_st_sections")}</span></div><div><b>${st.products}</b><span>${t("ob12_st_products")}</span></div>
        <div><b>${st.invoices}</b><span>${t("ob12_st_invoices")}</span></div><div><b>${st.from_invoice}</b><span>${t("ob12_st_matched")}</span></div>
        <div class="${st.to_place ? "warn" : ""}"><b>${st.to_place}</b><span>${t("ob12_st_to_place")}</span></div><div class="${st.no_cost ? "warn" : ""}"><b>${st.no_cost}</b><span>${t("ob12_st_no_cost")}</span></div></div>
      <p class="rc-summary">${t("ob12_summary").replace("{m}", st.from_invoice).replace("{p}", st.products).replace("{u}", st.to_place)}</p>
      ${st.invoices ? "" : `<div class="alert alert-warn">${t("ob12_no_invoices")}</div>`}
      ${P.total ? `<div class="alert alert-warn rc-pending" role="status">✎ ${t("ob13_pending").replace("{n}", P.total)} <button type="button" class="btn btn-sm btn-ghost" id="rc-reset">${t("ob13_undo_all")}</button></div>` : ""}
      <h3>${t("ob12_registered")}</h3><p class="muted small">${t("ob13_tap_hint")}</p>${report}
      ${(recon.deleted || []).length ? `<p class="muted small">${t("ob13_removed")} ${recon.deleted.map((d) => `${esc(d.name)} <button type="button" class="btn btn-sm btn-ghost" data-rc-restore="${d.id}">${t("ob13_undo")}</button>`).join(" · ")}</p>` : ""}
      ${unplaced}
      ${noCost.length && st.invoices ? `<section class="rc-nocost"><h3>⚑ ${t("ob12_nocost_title").replace("{n}", noCost.length)}</h3><p class="muted small">${t("ob12_nocost_hint")}</p>
        <ul class="chips">${noCost.map((r) => `<li class="chip static">${esc(r.name)} <span class="muted">· ${esc(r.sec)}</span></li>`).join("")}</ul></section>` : ""}
      ${recon.not_stocked.length ? `<p class="muted small">${t("ob12_ns_list")} ${recon.not_stocked.map((g) => esc(g.name)).join(", ")}</p>` : ""}
      ${okBox("rc-ok")}
      <div class="row ob-actions">
        <button type="button" class="btn btn-primary" id="rc-confirm">${un.length || st.from_invoice || P.total ? t("ob12_confirm") : t("ob12_continue")}</button>
        <button type="button" class="btn" id="rc-rerun">↻ ${t("ob12_rerun")}</button>
        <button type="button" class="btn btn-ghost" id="rc-back">← ${t("ob12_back_walk")}</button></div>
      <div id="rc-sheet" class="rc-sheet hidden" role="dialog" aria-modal="true" aria-labelledby="rc-sheet-title"></div>`);
    const capture = () => un.forEach((g, i) => { const a = $(`[data-rc-act="${i}"]`); if (!a) return;
      uState[g.key] = { act: a.value, sec: $(`[data-rc-sec="${i}"]`).value, nw: $(`[data-rc-new="${i}"]`).value, pick: $(`[data-rc-pick="${i}"]`).checked };
      const nm = $(`[data-rc-name="${i}"]`).value.trim(); if (nm && nm !== g.name) uOver[g.key] = { ...(uOver[g.key] || {}), name: nm }; });
    un.forEach((g, i) => { const u = uState[g.key]; if (!u) return;
      $(`[data-rc-act="${i}"]`).value = u.act; $(`[data-rc-sec="${i}"]`).value = u.sec; $(`[data-rc-new="${i}"]`).value = u.nw; $(`[data-rc-pick="${i}"]`).checked = u.pick; });
    const pend = async (body) => { capture(); const r = await post("/api/setup/reconcile/pending", body); await obReconcile(root, head, r); };
    const sheet = $("#rc-sheet");
    const closeSheet = () => { sheet.classList.add("hidden"); sheet.innerHTML = ""; document.body.classList.remove("sheet-open"); };
    const field = (id, label, val, type = "text", extra = "") => `<div><label for="${id}">${label}</label><input id="${id}" type="${type}" ${type === "number" ? 'min="0" step="any" inputmode="decimal"' : ""} value="${esc(val ?? "")}" ${extra}/></div>`;
    const openSheet = (title, body, onSave, extraBtns = "") => {
      sheet.innerHTML = `<div class="rc-sheet-bg" data-sheet-close></div><div class="rc-sheet-panel"><div class="rc-sheet-head"><h3 id="rc-sheet-title">${title}</h3>
        <button type="button" class="btn btn-sm btn-ghost" data-sheet-close aria-label="${t("btn_cancel")}">✕</button></div>${errBox("rc-sheet-err")}
        <div class="form-grid cols-2">${body}</div>
        <p class="muted small">${t("ob13_not_saved")}</p>
        <div class="row"><button type="button" class="btn btn-primary" id="rc-sheet-save">${t("ob13_apply_edit")}</button>${extraBtns}
        <button type="button" class="btn btn-ghost" data-sheet-close>${t("btn_cancel")}</button></div></div>`;
      sheet.classList.remove("hidden"); document.body.classList.add("sheet-open");
      $$("[data-sheet-close]", sheet).forEach((b) => b.addEventListener("click", closeSheet));
      $("#rc-sheet-save").addEventListener("click", () => guard("rc-sheet-err", async () => { await onSave(); closeSheet(); }));
      const f = $("input", sheet); if (f) f.focus();
    };
    const editRow = (id) => {
      const r = allRows.find((x) => x.id === id); if (!r) return;
      const others = allRows.filter((x) => x.id !== id);
      const lines = un.map((g) => opt(g.key, `“${g.name}”`)).join("");
      openSheet(`${t("ob13_edit")} · ${esc(r.name)}`, `
        ${field("rs-name", t("label_name"), r.name)}
        <div><label for="rs-zone">${t("label_zone")}</label><select id="rs-zone">${secOpts(r.zone)}</select></div>
        ${field("rs-oh", t("ob12_spoken"), r.spoken_qty, "number")}
        ${field("rs-unit", t("label_unit"), r.unit, "text", r.flags.includes("unit_differs") ? 'aria-describedby="rs-unit-note"' : "")}
        ${r.flags.includes("unit_differs") ? `<p class="small warn-text" id="rs-unit-note" style="grid-column:1/-1">⚑ ${t("ob13_unit_note").replace("{a}", esc(r.unit)).replace("{b}", esc(r.invoice_unit))}
          <button type="button" class="btn btn-sm" id="rs-use-inv">${t("ob13_use_invoice_unit").replace("{b}", esc(r.invoice_unit))}</button></p>` : ""}
        ${field("rs-pack", t("ob13_pack"), r.pack)}
        ${field("rs-cost", t("ob12_cost"), r.cost, "number")}
        ${field("rs-vendor", t("ob12_vendor"), r.vendor)}
        <div style="grid-column:1/-1" class="rc-links"><span class="label">${t("ob13_invoice_link")}</span>
          ${r.from_invoice ? `<p>“${esc(r.invoice_name)}” <button type="button" class="btn btn-sm" id="rs-unlink">${t("ob13_unlink")}</button></p>` : `<p class="muted small">${t("ob13_no_link")}</p>`}
          ${un.length ? `<div class="row"><select id="rs-link" aria-label="${t("ob13_link_line")}"><option value="">${t("ob13_link_line")}</option>${lines}</select><button type="button" class="btn btn-sm" id="rs-link-go">${t("ob13_link")}</button></div>` : ""}
          ${others.length && !r.pending_new ? `<div class="row"><select id="rs-merge" aria-label="${t("ob13_merge_into")}"><option value="">${t("ob13_merge_into")}</option>${others.map((o) => opt(o.id, o.name)).join("")}</select><button type="button" class="btn btn-sm" id="rs-merge-go">${t("ob13_merge")}</button></div>` : ""}
        </div>`, async () => {
        const ch = {}, val = (sel) => $(sel).value.trim();
        const cmp = { name: [val("#rs-name"), r.name], zone: [$("#rs-zone").value, r.zone], unit: [val("#rs-unit"), r.unit || ""], pack: [val("#rs-pack"), r.pack || ""], vendor: [val("#rs-vendor"), r.vendor || ""] };
        Object.entries(cmp).forEach(([k, [a, b]]) => { if (a !== b) ch[k] = a; });
        if (val("#rs-oh") !== String(r.spoken_qty ?? "")) ch.on_hand = val("#rs-oh");
        if (val("#rs-cost") !== String(r.cost ?? "")) ch.cost = val("#rs-cost");
        if (Object.keys(ch).length) await pend({ op: "edit", id, changes: ch });
      }, `<button type="button" class="btn btn-danger" id="rs-del">🗑 ${t("ob13_delete")}</button>`);
      const ui = $("#rs-use-inv"); if (ui) ui.addEventListener("click", () => { $("#rs-unit").value = r.invoice_unit; });
      $("#rs-del").addEventListener("click", () => guard("rc-sheet-err", async () => { closeSheet(); await pend({ op: "delete", id }); }));
      const ul = $("#rs-unlink"); if (ul) ul.addEventListener("click", () => guard("rc-sheet-err", async () => { closeSheet(); await pend({ op: "unlink", keys: r.invoice_keys }); }));
      const lg = $("#rs-link-go"); if (lg) lg.addEventListener("click", () => guard("rc-sheet-err", async () => { const v = $("#rs-link").value; if (!v) throw new Error(t("ob13_link_line")); closeSheet(); await pend({ op: "link", key: v, item_id: id });}));
      const mg = $("#rs-merge-go"); if (mg) mg.addEventListener("click", () => guard("rc-sheet-err", async () => { const v = $("#rs-merge").value; if (!v) throw new Error(t("ob13_merge_into")); closeSheet(); await pend({ op: "merge", id, into: v });}));
    };
    $$("[data-rc-row]").forEach((tr) => {
      tr.addEventListener("click", (e) => { if (!e.target.closest("button")) editRow(tr.dataset.rcRow); });
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target === tr) editRow(tr.dataset.rcRow); });
    });
    $$("[data-rc-edit]").forEach((b) => b.addEventListener("click", () => editRow(b.dataset.rcEdit)));
    $$("[data-rc-restore]").forEach((b) => b.addEventListener("click", () => guard("ob-error", () => pend({ op: "restore", id: b.dataset.rcRestore }))));
    const rs = $("#rc-reset"); if (rs) rs.addEventListener("click", () => guard("ob-error", () => pend({ op: "reset" })));
    $$("[data-rc-add]").forEach((b) => b.addEventListener("click", () => openSheet(`${t("ob13_add_title").replace("{section}", esc(O().zoneName(b.dataset.rcAdd)))}`,
      `${field("ra-name", t("label_name"), "")}${field("ra-oh", t("ob12_spoken"), "", "number")}${field("ra-unit", t("label_unit"), "ea")}`,
      async () => { await pend({ op: "add", zone: b.dataset.rcAdd, name: $("#ra-name").value, on_hand: $("#ra-oh").value, unit: $("#ra-unit").value }); })));
    $$("[data-rc-uedit]").forEach((b) => b.addEventListener("click", () => {
      const i = +b.dataset.rcUedit, g = un[i], o = { name: g.name, unit: g.unit, pack: g.pack, cost: g.unit_cost, vendor: g.vendors.join(", "), on_hand: "", ...(uOver[g.key] || {}) };
      openSheet(`${t("ob13_edit")} · “${esc(g.name)}”`, `${field("ru-name", t("label_name"), o.name)}${field("ru-oh", t("ob13_count_now"), o.on_hand, "number")}
        ${field("ru-unit", t("label_unit"), o.unit)}${field("ru-pack", t("ob13_pack"), o.pack)}${field("ru-cost", t("ob12_cost"), o.cost, "number")}${field("ru-vendor", t("ob12_vendor"), o.vendor)}
        ${allRows.length ? `<div style="grid-column:1/-1" class="row"><select id="ru-link" aria-label="${t("ob13_match_to")}"><option value="">${t("ob13_match_to")}</option>${allRows.map((r) => opt(r.id, r.name)).join("")}</select>
          <button type="button" class="btn btn-sm" id="ru-link-go">${t("ob13_link")}</button></div>` : ""}`,
        async () => { const v = (s) => $(s).value.trim(); uOver[g.key] = { name: v("#ru-name") || g.name, on_hand: v("#ru-oh"), unit: v("#ru-unit"), pack: v("#ru-pack"), cost: v("#ru-cost"), vendor: v("#ru-vendor") };
          capture(); uOver[g.key].name = v("#ru-name") || g.name; await obReconcile(root, head, recon); });
      const lg = $("#ru-link-go"); if (lg) lg.addEventListener("click", () => guard("rc-sheet-err", async () => { const v = $("#ru-link").value; if (!v) throw new Error(t("ob13_match_to")); closeSheet(); await pend({ op: "link", key: g.key, item_id: v });}));
    }));
    const sync = (i) => { const a = $(`[data-rc-act="${i}"]`).value;
      $(`[data-rc-sec="${i}"]`).classList.toggle("hidden", a !== "section");
      $(`[data-rc-new="${i}"]`).classList.toggle("hidden", a !== "new_section");
      $(`[data-rc-name="${i}"]`).classList.toggle("hidden", !["section", "new_section", "commissary"].includes(a)); };
    un.forEach((_, i) => { $(`[data-rc-act="${i}"]`).addEventListener("change", () => sync(i)); sync(i); });
    const picked = () => un.map((_, i) => i).filter((i) => $(`[data-rc-pick="${i}"]`).checked);
    const bulk = (act) => { const ps = picked(); if (!ps.length) { flash("ob-error", t("ob12_pick_some")); return; }
      ps.forEach((i) => { $(`[data-rc-act="${i}"]`).value = act; if (act === "section") $(`[data-rc-sec="${i}"]`).value = $("#rc-bulk-sec").value; sync(i); }); };
    if (un.length) {
      $("#rc-all").addEventListener("change", (e) => $$("[data-rc-pick]").forEach((c) => { c.checked = e.target.checked; }));
      $("#rc-bulk-put").addEventListener("click", () => bulk("section"));
      $("#rc-bulk-comm").addEventListener("click", () => bulk("commissary"));
      $("#rc-bulk-ns").addEventListener("click", () => bulk("not_stocked"));
      $("#rc-bulk-skip").addEventListener("click", () => bulk("skip"));
    }
    $("#rc-back").addEventListener("click", () => { walkIdx = secs.length - 1; setPhase("walk"); });
    $("#rc-rerun").addEventListener("click", () => renderOnboarding());
    $("#rc-confirm").addEventListener("click", () => guard("ob-error", async () => {
      const instructions = un.map((g, i) => {
        const action = $(`[data-rc-act="${i}"]`).value, ov = uOver[g.key] || {};
        const o = { key: g.key, action, unit: ov.unit, pack: ov.pack, cost: ov.cost, vendor: ov.vendor, on_hand: ov.on_hand, name: $(`[data-rc-name="${i}"]`).value.trim() };
        if (action === "section") { o.section = $(`[data-rc-sec="${i}"]`).value; if (!o.section) throw new Error(t("ob12_need_section").replace("{name}", g.name)); }
        if (action === "new_section") { o.section_name = $(`[data-rc-new="${i}"]`).value.trim(); if (!o.section_name) throw new Error(t("ob12_need_new").replace("{name}", g.name)); }
        if (action === "same_as") o.item_id = g.maybe.id;
        return o;
      });
      if (instructions.length || st.from_invoice || P.total) await post("/api/setup/reconcile/apply", { carry: true, instructions });
      await loadSections();
      await setPhase("review");
    }));
  }

  async function obReview(root, head) {
    const items = (await api("/api/items")).items || [];
    root.innerHTML = head + card(`<h2>${t("ob11_review_title")}</h2><p class="muted">${t("ob11_review_hint")}</p>${errBox("ob-error")}
      ${items.length ? secs.map((s) => { const its = items.filter((i) => i.zone === s.key); return `<section class="rv-sec"><h3>${O().zoneBadge(s.key)} <span class="muted">${its.length} ${t("sec_products")}</span></h3>
        ${its.length ? `<div class="table-wrap"><table><thead><tr><th>${t("label_item")}</th><th>${t("label_unit")}</th><th>${t("label_zone")}</th><th>PAR</th></tr></thead><tbody>
        ${its.map((i) => `<tr><td><input data-rv-name="${i.id}" value="${esc(i.name)}" aria-label="${t("label_item")}" /></td><td>${esc(i.unit)}</td>
          <td><select data-rv-zone="${i.id}" aria-label="${t("label_zone")}">${secs.map((x) => opt(x.key, secName(x), x.key === i.zone)).join("")}</select></td>
          <td><input type="number" min="0" step="any" inputmode="decimal" data-rv-par="${i.id}" value="${i.par ?? 0}" aria-label="PAR" /></td></tr>`).join("")}</tbody></table></div>` : `<p class="muted">${t("ob11_empty_section")}</p>`}</section>`; }).join("")
      : `<div class="alert alert-warn">${t("ob_no_items")}</div>`}
      <div class="row ob-actions"><button type="button" class="btn btn-primary" id="rv-save">${items.length ? t("ob11_approve") : t("ob11_finish_empty")}</button>
      <button type="button" class="btn btn-ghost" id="rv-back">${t("btn_back")}</button></div>`);
    $("#rv-back").addEventListener("click", () => setPhase("reconcile"));
    $("#rv-save").addEventListener("click", () => guard("ob-error", async () => {
      for (const i of items) {
        const par = $(`[data-rv-par="${i.id}"]`).value, zone = $(`[data-rv-zone="${i.id}"]`).value, name = $(`[data-rv-name="${i.id}"]`).value.trim();
        if (String(par) !== String(i.par) || zone !== i.zone || (name && name !== i.name)) await put(`/api/items/${i.id}`, { par, zone, name: name || i.name });
      }
      countIdx = 0;
      await setPhase(items.length ? "first_count" : "account");
    }));
  }

  /* Pass 2 — first live count, section by section */
  async function obCount(root, head) {
    const all = (await api("/api/items")).items || [];
    const live = secs.filter((s) => all.some((i) => i.zone === s.key));
    if (!live.length) return setPhase("account");
    if (countIdx >= live.length) countIdx = live.length - 1;
    const s = live[countIdx];
    const items = all.filter((i) => i.zone === s.key);
    root.innerHTML = head + card(`<div class="sec-progress">${live.map((x, i) => `<span class="sec-pill ${i === countIdx ? "on" : i < countIdx ? "has" : ""}">${esc(secName(x))}</span>`).join("")}</div>
      <h2>${t("ob11_count_title").replace("{section}", esc(secName(s)))}</h2><p>${t("ob11_count_hint")}</p>${errBox("ob-error")}
      ${V().micBlock("fc", "ob11_count_ph")}
      <button type="button" class="btn" id="fc-hear">${t("ob11_fill_from_voice")}</button>
      <div id="fc-note"></div>
      <div class="table-wrap"><table><thead><tr><th>${t("label_item")}</th><th>${t("label_unit")}</th><th>${t("qty")}</th></tr></thead><tbody>
      ${items.map((i) => `<tr><td>${esc(i.name)}</td><td>${esc(i.unit)}</td><td><input type="number" min="0" step="any" inputmode="decimal" data-fc="${i.id}" value="${i.on_hand ?? 0}" aria-label="${esc(i.name)}" /></td></tr>`).join("")}</tbody></table></div>
      <div class="row ob-actions"><button type="button" class="btn btn-primary" id="fc-save">${countIdx < live.length - 1 ? t("ob11_save_next_section") : t("ob11_save_finish_count")}</button>
      <button type="button" class="btn btn-ghost" id="fc-back">← ${t("btn_back")}</button>
      <button type="button" class="btn btn-ghost" id="fc-skip">${t("ob_first_skip")}</button></div>`);
    V().attachMic($("#fc-mic"), $("#fc-text"), $("#fc-mic-status"));
    $("#fc-hear").addEventListener("click", () => guard("ob-error", async () => {
      const r = await post("/api/voice/parse", { text: $("#fc-text").value, scope: "all" });
      let n = 0; const miss = [];
      (r.lines || []).forEach((l) => { const el = l.item_id && $(`[data-fc="${l.item_id}"]`); if (el && l.qty != null) { el.value = l.qty; el.classList.add("filled"); n++; } else miss.push(l.spoken || l.raw || ""); });
      $("#fc-note").innerHTML = `<p class="muted">${t("ob11_filled").replace("{n}", n)}${miss.filter(Boolean).length ? ` · ${t("ob11_not_here")}: ${esc(miss.filter(Boolean).join(", "))}` : ""}</p>`;
    }));
    $("#fc-back").addEventListener("click", () => { if (countIdx === 0) setPhase("review"); else { countIdx--; renderOnboarding(); } });
    $("#fc-skip").addEventListener("click", () => setPhase("account"));
    $("#fc-save").addEventListener("click", () => guard("ob-error", async () => {
      const counts = {}; $$("[data-fc]").forEach((el) => { if (el.value !== "") counts[el.dataset.fc] = Number(el.value); });
      await post(`/api/sections/${encodeURIComponent(s.key)}/count`, { counts });
      if (countIdx < live.length - 1) { countIdx++; return renderOnboarding(); }
      await post("/api/onboarding/first-count");
      await setPhase("account");
    }));
  }

  function obAccount(root, head) {
    root.innerHTML = head + card(`<h2>${t("ob11_account_title")}</h2><p class="muted">${t("ob11_account_hint")}</p>${errBox("ob-error")}
      ${ob.has_admin ? `<div class="alert alert-ok">${t("ob_account_done")}</div><button type="button" class="btn btn-primary" id="ob-next">${t("btn_next")}</button>` : `
      <form id="ob-acct" class="form-grid cols-2" novalidate>
        <div><label for="ob-uname">${t("label_your_name")}</label><input id="ob-uname" autocomplete="name" /></div>
        <div><label for="ob-ulogin">${t("label_login")}</label><input id="ob-ulogin" autocapitalize="off" /></div>
        <div><label for="ob-pin">${t("label_pin")}</label><input id="ob-pin" type="password" inputmode="numeric" maxlength="6" class="pin-input" /></div>
        <div><label for="ob-pin2">${t("label_pin_again")}</label><input id="ob-pin2" type="password" inputmode="numeric" maxlength="6" class="pin-input" /></div>
        <div class="row" style="grid-column:1/-1"><button type="submit" class="btn btn-primary">${t("ob_create_admin")}</button>
        <button type="button" class="btn btn-ghost" id="ob-skip">${t("ob11_skip_lock")}</button></div>
      </form>`}`);
    if (ob.has_admin) { $("#ob-next").addEventListener("click", () => setPhase("done")); return; }
    $("#ob-uname").addEventListener("input", (e) => { const l = $("#ob-ulogin"); if (!l.dataset.touched) l.value = e.target.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "."); });
    $("#ob-ulogin").addEventListener("input", (e) => { e.target.dataset.touched = "1"; });
    $("#ob-skip").addEventListener("click", () => setPhase("done"));
    $("#ob-acct").addEventListener("submit", (e) => { e.preventDefault(); guard("ob-error", async () => {
      if ($("#ob-pin").value !== $("#ob-pin2").value) throw new Error(t("pin_mismatch"));
      await post("/api/people", { name: $("#ob-uname").value, login: $("#ob-ulogin").value, role: "admin", pin: $("#ob-pin").value });
      await V().refreshAuth();
      await setPhase("done");
    }); });
  }

  function obDone(root) {
    root.innerHTML = card(`<div class="ob-welcome"><img src="/static/img/seal.webp" alt="" width="140" height="141" />
      <h1>${t("ob_done_title")}</h1><p>${t("ob11_done_body")}</p>
      <button type="button" class="btn btn-primary" id="ob-finish">${t("ob_go_home")}</button></div>`);
    $("#ob-finish").addEventListener("click", () => { ob = null; V().finishOnboarding(); });
  }

  /* ---------- Invoice upload + optional AI read (enhances the v1 invoice view) ---------- */
  async function enhanceInvoice() {
    await loadAI();
    const root = $("#invoice-root");
    let files = [];
    const wrap = document.createElement("div");
    wrap.innerHTML = card(`<h2>📎 ${t("inv11_upload_title")}</h2>
      <p class="muted">${aiOn() ? t("inv11_hint_ai") : t("inv11_hint_manual")}</p>${errBox("inv11-error")}${okBox("inv11-ok")}
      <div class="row">
        <label class="btn" for="inv11-files">📄 ${t("inv11_choose")}</label><input id="inv11-files" type="file" multiple accept="image/*,application/pdf" class="sr" />
        <label class="btn" for="inv11-cam">📷 ${t("inv11_snap")}</label><input id="inv11-cam" type="file" accept="image/*" capture="environment" class="sr" />
      </div>
      <div id="inv11-attached"></div>
      <div id="inv11-review"></div>
      ${aiOn() ? "" : `<p class="muted small">${t("inv11_ai_off")} <a href="#" data-goto="ai">${t("inv11_turn_on")}</a></p>`}`);
    root.prepend(wrap);
    const drawFiles = () => {
      $("#inv11-attached").innerHTML = files.length ? `<ul class="chips">${files.map((f) => `<li class="chip static"><a href="${esc(f.url)}" target="_blank" rel="noopener">${f.type === "application/pdf" ? "📄" : "🖼️"} ${esc(f.name)}</a></li>`).join("")}</ul>
        <div class="row">${aiOn() ? `<button type="button" class="btn btn-primary" id="inv11-read">✨ ${t("inv11_read_ai")}</button>` : `<span class="muted">${t("inv11_attached_manual")}</span>`}
        <button type="button" class="btn btn-ghost" id="inv11-clear">${t("inv11_clear")}</button></div>` : "";
      if (!files.length) return;
      $("#inv11-clear").addEventListener("click", () => { files = []; window.OSFT_V11.invoiceFiles = []; drawFiles(); $("#inv11-review").innerHTML = ""; });
      const rd = $("#inv11-read");
      if (rd) rd.addEventListener("click", () => guard("inv11-error", async () => {
        rd.disabled = true; $("#inv11-review").innerHTML = `<p class="muted">${t("ob11_ai_reading")}</p>`;
        try { const r = await post("/api/ai/invoice", { files: files.map((f) => f.name) }); await drawReview(r.invoice); }
        finally { rd.disabled = false; }
      }).then((v) => { if (v === null) $("#inv11-review").innerHTML = ""; }));
    };
    const onPick = (input) => input.addEventListener("change", () => guard("inv11-error", async () => {
      if (!input.files.length) return;
      const f = new FormData(); [...input.files].forEach((x) => f.append("files", x));
      const r = await upload("/api/invoice/upload", f);
      files = files.concat(r.files).slice(0, 6);
      window.OSFT_V11.invoiceFiles = files.map((x) => x.name);
      input.value = ""; drawFiles();
    }));
    onPick($("#inv11-files")); onPick($("#inv11-cam"));
    $$("[data-goto]", wrap).forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); O().showView(a.dataset.goto); }));

    async function drawReview(inv) {
      const items = (await api("/api/items")).items || [];
      let vendors = [];
      try { vendors = (await api("/api/vendors")).vendors; } catch (_) { vendors = []; }
      const lines = inv.lines.map((l) => ({ ...l, pick: l.item_id || "__new" }));
      $("#inv11-review").innerHTML = `<h3>${t("inv11_review_title")}</h3><p class="muted small">✨ ${t("inv11_review_note")}</p>
        <div class="form-grid cols-3">
          <div><label for="inv11-vendor">${t("label_vendor")}</label><input id="inv11-vendor" list="inv11-vlist" value="${esc(inv.vendor || "")}" /><datalist id="inv11-vlist">${vendors.map((v) => `<option value="${esc(v.name)}">`).join("")}</datalist></div>
          <div><label for="inv11-no">${t("label_invoice_no")}</label><input id="inv11-no" value="${esc(inv.invoice_no || "")}" /></div>
          <div><label for="inv11-date">${t("label_date")}</label><input id="inv11-date" type="date" value="${esc(inv.date || "")}" /></div>
        </div>
        <div class="table-wrap"><table class="inv11-table"><thead><tr><th>${t("ob11_keep")}</th><th>${t("invoice_line")}</th><th>${t("inv11_product")}</th><th>${t("qty")}</th><th>${t("label_unit")}</th><th>${t("label_unit_cost")}</th></tr></thead><tbody>
        ${lines.map((l, i) => `<tr><td><input type="checkbox" data-iv-keep="${i}" checked aria-label="${t("ob11_keep")}" /></td>
          <td class="muted iv-desc">${esc(l.description)}${l.total != null ? `<div class="small">${t("inv11_line_total")} ${O().money(l.total)}</div>` : ""}</td>
          <td class="iv-prod"><select data-iv-pick="${i}" aria-label="${t("inv11_product")}"><option value="__new" ${l.pick === "__new" ? "selected" : ""}>＋ ${t("inv11_new_product")}</option>${items.map((it) => opt(it.id, `${it.name} (${it.unit})`, it.id === l.pick)).join("")}</select>
            <div data-iv-newbox="${i}" class="${l.pick === "__new" ? "" : "hidden"} iv-new"><input data-iv-newname="${i}" value="${esc(l.description)}" aria-label="${t("label_name")}" />
            <select data-iv-newzone="${i}" aria-label="${t("label_zone")}">${secs.map((s) => opt(s.key, secName(s))).join("")}</select></div>
            ${l.status === "ambiguous" ? `<div class="small warn">${t("inv11_check_match")}</div>` : ""}</td>
          <td data-l="${esc(t("qty"))}"><input type="number" min="0" step="any" data-iv-qty="${i}" value="${l.qty ?? ""}" aria-label="${t("qty")}" /></td>
          <td data-l="${esc(t("label_unit"))}"><input data-iv-unit="${i}" value="${esc(l.unit || "")}" size="5" aria-label="${t("label_unit")}" /></td>
          <td data-l="${esc(t("label_unit_cost"))}"><input type="number" min="0" step="any" data-iv-cost="${i}" value="${l.unit_cost ?? ""}" aria-label="${t("label_unit_cost")}" /></td></tr>`).join("")}</tbody></table></div>
        ${inv.total != null ? `<p class="muted">${t("inv11_inv_total")}: ${O().money(inv.total)}</p>` : ""}
        <button type="button" class="btn btn-primary" id="inv11-save">${t("inv11_save")}</button>`;
      if (!secs.length) await loadSections();
      $$("[data-iv-pick]").forEach((s) => s.addEventListener("change", () => $(`[data-iv-newbox="${s.dataset.ivPick}"]`).classList.toggle("hidden", s.value !== "__new")));
      $("#inv11-save").addEventListener("click", () => guard("inv11-error", async () => {
        const out = [];
        lines.forEach((l, i) => {
          if (!$(`[data-iv-keep="${i}"]`).checked) return;
          const qty = Number($(`[data-iv-qty="${i}"]`).value);
          if (!(qty > 0)) return;
          const pick = $(`[data-iv-pick="${i}"]`).value, cost = $(`[data-iv-cost="${i}"]`).value;
          const row = { qty, unit_cost: cost === "" ? null : Number(cost) };
          if (pick === "__new") row.new_item = { name: $(`[data-iv-newname="${i}"]`).value.trim(), unit: $(`[data-iv-unit="${i}"]`).value.trim() || "ea", zone: $(`[data-iv-newzone="${i}"]`).value };
          else row.item_id = pick;
          out.push(row);
        });
        if (!out.length) throw new Error(t("pick_one"));
        const r = await post("/api/receives/batch", { vendor: $("#inv11-vendor").value, invoice_no: $("#inv11-no").value, date: $("#inv11-date").value, photos: files.map((f) => f.name), lines: out });
        files = []; window.OSFT_V11.invoiceFiles = []; drawFiles();
        $("#inv11-review").innerHTML = "";
        flash("inv11-ok", `${r.receives.length} ${t("lines_received")}`);
      }));
    }
  }

  window.OSFT_V11 = { renderOnboarding, renderSectionsView, renderAIView, enhanceInvoice, prime, invoiceFiles: [] };
})();
