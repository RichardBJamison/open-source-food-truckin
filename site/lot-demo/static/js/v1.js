/* OSFT v1.0 — OSBW parity views: onboarding, PIN login, speak-your-inventory, starter list,
   product import/export, purchase orders, invoice receive, input log, money reports, trucks,
   staff board, people & access, vendors, categories/GL, POS accounts, backups. */
(function () {
  "use strict";
  const O = () => window.OSFT;
  const t = (k) => O().t(k);
  const esc = (s) => O().esc(s);
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const api = (p, o) => O().api(p, o);
  const post = (p, body) => api(p, { method: "POST", body: JSON.stringify(body || {}) });
  const put = (p, body) => api(p, { method: "PUT", body: JSON.stringify(body || {}) });
  const del = (p) => api(p, { method: "DELETE" });
  const num = (n) => O().fmtNum(n);
  const money = (n) => O().money(n);
  const when = (s) => O().fmtWhen(s);
  const zoneLabel = (z) => (O().zoneName ? O().zoneName(z) : t("zone_" + z));
  let auth = { auth_enabled: false, user: null, people: [] };
  let business = {};

  function card(inner, cls = "") { return `<div class="card ${cls}">${inner}</div>`; }
  function errBox(id) { return `<div id="${id}" class="alert alert-error hidden" role="alert"></div>`; }
  function okBox(id) { return `<div id="${id}" class="alert alert-ok hidden" role="status"></div>`; }
  function flash(id, msg) { const el = document.getElementById(id); if (!el) return; el.textContent = msg; el.classList.remove("hidden"); }
  function hide(id) { const el = document.getElementById(id); if (el) el.classList.add("hidden"); }
  async function guard(errId, fn) {
    hide(errId);
    try { return await fn(); } catch (e) { flash(errId, e.message); return null; }
  }
  function opt(v, label, sel) { return `<option value="${esc(v)}" ${sel ? "selected" : ""}>${esc(label)}</option>`; }
  function can(perm) {
    if (!auth.auth_enabled) return true;
    const u = auth.user;
    return !!u && (u.role === "admin" || !!(u.permissions || {})[perm]);
  }
  function download(name, text, type = "text/plain") {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name; document.body.appendChild(a); a.click(); a.remove();
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (_) {
      const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
      let ok = false; try { ok = document.execCommand("copy"); } catch (__) { ok = false; } ta.remove(); return ok;
    }
  }

  /* ---------- Microphone (Web Speech API) with typed fallback ---------- */
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  function attachMic(btn, textarea, statusEl) {
    if (!SR) {
      btn.disabled = true;
      btn.title = t("mic_unsupported");
      if (statusEl) statusEl.textContent = t("mic_unsupported");
      return;
    }
    let rec = null;
    let on = false;
    const stop = () => { on = false; btn.classList.remove("listening"); btn.textContent = "🎙️ " + t("btn_mic_start"); if (rec) try { rec.stop(); } catch (_) { /* already stopped */ } };
    btn.addEventListener("click", () => {
      if (on) return stop();
      rec = new SR();
      rec.lang = O().locale === "es" ? "es-US" : "en-US";
      rec.continuous = true;
      rec.interimResults = true;
      const base = textarea.value ? textarea.value.replace(/\s*$/, "") + "\n" : "";
      let finalText = "";
      rec.onresult = (ev) => {
        let interim = "";
        for (let i = ev.resultIndex; i < ev.results.length; i++) {
          const r = ev.results[i];
          if (r.isFinal) finalText += r[0].transcript.trim() + ", ";
          else interim += r[0].transcript;
        }
        textarea.value = base + finalText + interim;
        if (statusEl) statusEl.textContent = t("mic_listening");
      };
      rec.onerror = (ev) => { if (statusEl) statusEl.textContent = t("mic_error") + " (" + ev.error + ")"; stop(); };
      rec.onend = () => { if (on) { try { rec.start(); } catch (_) { stop(); } } else if (statusEl) statusEl.textContent = t("mic_stopped"); };
      try { rec.start(); on = true; btn.classList.add("listening"); btn.textContent = "⏹ " + t("btn_mic_stop"); if (statusEl) statusEl.textContent = t("mic_listening"); }
      catch (e) { if (statusEl) statusEl.textContent = t("mic_error") + " " + e.message; }
    });
    btn.textContent = "🎙️ " + t("btn_mic_start");
  }
  function micBlock(prefix, placeholderKey) {
    return `<div class="voice-box">
      <div class="row"><button type="button" class="btn btn-primary mic-btn" id="${prefix}-mic">🎙️ ${t("btn_mic_start")}</button>
      <span class="muted" id="${prefix}-mic-status">${SR ? t("mic_ready") : t("mic_unsupported")}</span></div>
      <label for="${prefix}-text" class="sr">${t("voice_text_label")}</label>
      <textarea id="${prefix}-text" rows="6" class="voice-text" placeholder="${esc(t(placeholderKey))}"></textarea>
    </div>`;
  }

  /* ---------- Sidebar user + truck switch ---------- */
  async function refreshAuth() {
    try { auth = await api("/api/auth/status"); } catch (_) { /* keep */ }
    const el = $("#sidebar-user");
    if (!el) return;
    if (!auth.auth_enabled) el.innerHTML = `<p class="muted">${t("open_mode")}</p><button type="button" class="btn btn-sm" data-goto="people">${t("btn_add_pin")}</button>`;
    else if (auth.user) el.innerHTML = `<p><b>${esc(auth.user.name)}</b> <span class="badge">${esc(t("role_" + auth.user.role))}</span></p><button type="button" class="btn btn-sm" id="btn-logout">${t("btn_logout")}</button>`;
    else el.innerHTML = "";
    const lo = $("#btn-logout");
    if (lo) lo.addEventListener("click", async () => { await post("/api/auth/logout"); await refreshAuth(); O().showView("login"); });
  }
  async function refreshTrucks() {
    const box = $("#truck-switch");
    if (!box) return;
    try {
      const r = await api("/api/trucks");
      if (r.trucks.length < 2) { box.innerHTML = ""; return; }
      box.innerHTML = `<label for="truck-pick" class="sr">${t("tab_trucks")}</label><select id="truck-pick">${r.trucks.map((x) => opt(x.id, x.name, x.id === r.active_truck_id)).join("")}</select>`;
      $("#truck-pick").addEventListener("change", async (e) => { await post(`/api/trucks/${e.target.value}/activate`); await afterTruckChange(); });
    } catch (_) { box.innerHTML = ""; }
  }
  async function afterTruckChange() {
    const s = await api("/api/settings");
    $("#truck-label").textContent = s.settings.truck_name || business.name || "OSFT";
    await refreshTrucks();
    O().refreshView(O().currentView);
  }

  /* ---------- Login (6-digit PIN, OSBW People & access) ---------- */
  async function renderLogin() {
    document.body.classList.add("focus-mode");
    await refreshAuth();
    const root = $("#login-root");
    root.innerHTML = card(`<div class="login-box">
      <img src="/static/img/seal.webp" alt="" width="110" height="111" />
      <h1>${t("login_title")}</h1>
      <p class="muted">${esc(business.name || "")}</p>
      ${errBox("login-error")}
      <label for="login-who">${t("login_who")}</label>
      <select id="login-who"><option value="">${t("login_any")}</option>${(auth.people || []).map((p) => opt(p.id, p.name)).join("")}</select>
      <label for="login-pin">${t("label_pin")}</label>
      <input id="login-pin" type="password" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="one-time-code" class="pin-input" />
      <div class="pin-pad">${[1, 2, 3, 4, 5, 6, 7, 8, 9, "⌫", 0, "✓"].map((k) => `<button type="button" class="btn pin-key" data-k="${k}">${k}</button>`).join("")}</div>
    </div>`, "login-card");
    const pin = $("#login-pin");
    const submit = () => guard("login-error", async () => {
      await post("/api/auth/login", { pin: pin.value, user_id: $("#login-who").value || undefined });
      pin.value = "";
      document.body.classList.remove("focus-mode");
      await refreshAuth();
      await refreshTrucks();
      await O().syncZones();
      O().showView("home");
    });
    $$(".pin-key", root).forEach((b) => b.addEventListener("click", () => {
      const k = b.dataset.k;
      if (k === "⌫") pin.value = pin.value.slice(0, -1);
      else if (k === "✓") submit();
      else if (pin.value.length < 6) { pin.value += k; if (pin.value.length === 6) submit(); }
    }));
    pin.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    pin.addEventListener("input", () => { if (pin.value.length === 6) submit(); });
    pin.focus();
  }

  /* ---------- Onboarding: the v1.1 first run lives in v11.js (OSFT_V11.renderOnboarding) ---------- */
  let ob = null;
  async function finishOnboarding(goto) {
    document.body.classList.remove("focus-mode");
    ob = null;
    const s = await api("/api/settings").catch(() => ({ settings: {} }));
    const b = await api("/api/business").catch(() => ({ business: {} }));
    business = b.business || {};
    $("#truck-label").textContent = s.settings.truck_name || business.name || "OSFT";
    await refreshAuth();
    await refreshTrucks();
    O().showView(goto || "home");
  }

  /* ---------- Speak your inventory (voice count) ---------- */
  let voiceResult = null;
  let voiceItems = [];
  async function renderVoice() {
    const root = $("#voice-root");
    voiceItems = (await api("/api/items")).items || [];
    const zs = O().zones;
    root.innerHTML = card(`<h2>🎙️ ${t("tab_voice_title")}</h2>
      <p class="muted">${t("voice_hint")}</p>
      <div class="chips" role="group" aria-label="${t("label_zone")}">${zs.map((z) => `<button type="button" class="chip" data-vzone="${z}">${O().zoneBadge(z)}</button>`).join("")}</div>
      ${micBlock("voice", "voice_placeholder")}
      ${errBox("voice-error")}
      <div class="row"><button type="button" class="btn btn-primary" id="voice-check">${t("btn_check_count")}</button>
        <label class="check"><input type="checkbox" id="voice-scope-all" /> ${t("voice_scope_all")}</label>
        <button type="button" class="btn btn-ghost" id="voice-clear">${t("btn_clear")}</button></div>
      <p class="muted small">${t("voice_tips")}</p>`) + `<div id="voice-review"></div>`;
    attachMic($("#voice-mic"), $("#voice-text"), $("#voice-mic-status"));
    $$("[data-vzone]", root).forEach((b) => b.addEventListener("click", () => {
      const ta = $("#voice-text");
      ta.value = (ta.value ? ta.value.replace(/\s*$/, "") + "\n" : "") + zoneLabel(b.dataset.vzone) + ": ";
      ta.focus();
    }));
    $("#voice-clear").addEventListener("click", () => { $("#voice-text").value = ""; $("#voice-review").innerHTML = ""; voiceResult = null; });
    $("#voice-check").addEventListener("click", checkVoice);
  }
  async function checkVoice() {
    await guard("voice-error", async () => {
      voiceResult = await post("/api/voice/parse", { text: $("#voice-text").value, scope: $("#voice-scope-all").checked ? "all" : "mentioned" });
      renderVoiceReview();
    });
  }
  const STATUS_CLS = { matched: "ok", unit_check: "warn", ambiguous: "warn", unmatched: "bad", no_qty: "bad" };
  function renderVoiceReview() {
    const r = voiceResult;
    const box = $("#voice-review");
    const s = r.summary;
    const itemOpts = (sel) => `<option value="">${t("voice_pick_item")}</option>` + voiceItems.map((i) => opt(i.id, `${i.name} (${i.unit})`, i.id === sel)).join("");
    box.innerHTML = card(`<div class="panel-head-row"><h2>${t("voice_review_title")}</h2><span class="caption">${s.heard} ${t("voice_heard")}</span></div>
      <div class="metrics-grid voice-sum">
        <div class="metric metric--teal"><span class="metric-n">${s.matched}</span><span class="metric-l">${t("voice_matched")}</span></div>
        <div class="metric metric--orange"><span class="metric-n">${s.unit_check + s.ambiguous}</span><span class="metric-l">${t("voice_check")}</span></div>
        <div class="metric metric--hot"><span class="metric-n">${s.unmatched + s.no_qty}</span><span class="metric-l">${t("voice_unresolved")}</span></div>
        <div class="metric metric--pop"><span class="metric-n">${s.missing}</span><span class="metric-l">${t("voice_missing")}</span></div>
      </div>
      <div class="table-wrap"><table class="voice-table"><thead><tr><th>${t("voice_you_said")}</th><th>${t("label_item")}</th><th>${t("qty")}</th><th>${t("voice_ignore")}</th></tr></thead><tbody>
      ${r.lines.map((l) => `<tr data-vl="${l.n}" class="vl-${STATUS_CLS[l.status]}">
        <td>“${esc(l.raw)}”<div><span class="badge vbadge-${STATUS_CLS[l.status]}">${t("vstatus_" + l.status)}</span>${l.zone ? " " + O().zoneBadge(l.zone) : ""}
          ${l.note ? `<span class="muted"> ${esc(noteText(l.note))}</span>` : ""}</div></td>
        <td><select data-vl-item="${l.n}">${itemOpts(l.item_id)}</select></td>
        <td><input type="number" min="0" step="any" inputmode="decimal" data-vl-qty="${l.n}" value="${l.qty ?? ""}" /> <span class="muted" data-vl-unit="${l.n}">${esc(l.item_unit || "")}</span></td>
        <td><input type="checkbox" data-vl-ignore="${l.n}" aria-label="${t("voice_ignore")}" /></td></tr>`).join("")}</tbody></table></div>
      ${r.missing.length ? `<h3>${t("voice_not_said")} (${r.missing.length})</h3><p class="muted">${t("voice_not_said_hint")}</p>
        <div class="missing-list">${r.missing.map((m) => `<label class="check"><input type="checkbox" data-vm-zero="${m.item_id}" /> ${esc(m.name)} ${O().zoneBadge(m.zone)} <span class="muted">${t("voice_set_zero")}</span></label>`).join("")}</div>` : ""}
      ${errBox("voice-apply-error")}
      <p id="voice-gap" class="muted"></p>
      <div class="row"><button type="button" class="btn" id="voice-save">${t("btn_voice_save")}</button>
      <button type="button" class="btn btn-primary" id="voice-finish">${t("btn_voice_finish")}</button></div>`);
    $$("[data-vl-item]", box).forEach((s2) => s2.addEventListener("change", () => {
      const it = voiceItems.find((i) => i.id === s2.value);
      $(`[data-vl-unit="${s2.dataset.vlItem}"]`).textContent = it ? it.unit : "";
      updateGap();
    }));
    $$("[data-vl-qty],[data-vl-ignore]", box).forEach((x) => x.addEventListener("input", updateGap));
    $$("[data-vl-ignore]", box).forEach((x) => x.addEventListener("change", updateGap));
    $("#voice-save").addEventListener("click", () => applyVoice(false));
    $("#voice-finish").addEventListener("click", () => applyVoice(true));
    updateGap();
  }
  function noteText(n) {
    if (!n) return "";
    return n.split("; ").map((p) => p.startsWith("unit_mismatch") ? t("voice_unit_mismatch") + " " + p.split(":")[1] : p).join("; ");
  }
  function voiceCounts() {
    const counts = {};
    let unresolved = 0;
    for (const l of voiceResult.lines) {
      if ($(`[data-vl-ignore="${l.n}"]`).checked) continue;
      const id = $(`[data-vl-item="${l.n}"]`).value;
      const q = $(`[data-vl-qty="${l.n}"]`).value;
      if (!id || q === "") { unresolved++; continue; }
      counts[id] = Math.round(((counts[id] || 0) + Number(q)) * 10000) / 10000;
    }
    return { counts, unresolved };
  }
  function updateGap() {
    const { counts, unresolved } = voiceCounts();
    const tol = voiceResult.gap_tolerance;
    const ok = unresolved <= tol && Object.keys(counts).length > 0;
    $("#voice-gap").textContent = unresolved ? `${unresolved} ${t("voice_left_to_fix")} (${t("voice_tolerance")} ${tol})` : t("voice_all_set");
    $("#voice-finish").disabled = !ok;
    $("#voice-save").disabled = !Object.keys(counts).length;
  }
  async function applyVoice(complete) {
    await guard("voice-apply-error", async () => {
      const { counts } = voiceCounts();
      const zero = $$("[data-vm-zero]").filter((c) => c.checked).map((c) => c.dataset.vmZero);
      const r = await post("/api/voice/apply", { counts, text: $("#voice-text").value, complete, zero_missing: zero });
      if (complete) { voiceResult = null; O().showView("variance"); }
      else {
        $("#voice-review").innerHTML = `<div class="alert alert-ok">${r.saved} ${t("voice_saved_keep")}</div>`;
        $("#voice-text").value = "";
      }
    });
  }

  /* ---------- Starter catalog picker ---------- */
  async function renderStarter(root, after) {
    root = root || $("#starter-root");
    const r = await api("/api/catalog/starter");
    const es = O().locale === "es";
    root.innerHTML = card(`<div class="panel-head-row"><h2>📚 ${t("tab_starter_title")}</h2><span class="caption">${r.count} ${t("products")}</span></div>
      <p class="muted">${t("starter_hint")}</p>
      <div class="row"><input type="search" id="st-q" placeholder="${esc(t("search_products"))}" style="flex:1" />
      <select id="st-cat"><option value="">${t("all_categories")}</option>${r.categories.map((c) => opt(c, c)).join("")}</select></div>
      ${errBox("st-error")}${okBox("st-ok")}
      <div id="st-list" class="starter-list"></div>
      <div class="row sticky-actions"><span id="st-count" class="muted">0 ${t("selected")}</span>
      <button type="button" class="btn btn-primary" id="st-add">${t("btn_add_selected")}</button>
      ${after ? `<button type="button" class="btn btn-ghost" id="st-done">${t("btn_next")}</button>` : ""}</div>`);
    const chosen = new Set();
    const draw = () => {
      const q = $("#st-q", root).value.trim().toLowerCase();
      const cat = $("#st-cat", root).value;
      const rows = r.items.filter((c) => (!cat || c.category === cat) && (!q || (c.name + " " + (c.name_es || "")).toLowerCase().includes(q)));
      const groups = {};
      rows.forEach((c) => (groups[c.category] = groups[c.category] || []).push(c));
      $("#st-list", root).innerHTML = Object.entries(groups).map(([g, cs]) => `<fieldset class="starter-group"><legend>${esc(g)} <button type="button" class="btn btn-sm btn-ghost" data-st-all="${esc(g)}">${t("select_all")}</button></legend>
        ${cs.map((c) => `<label class="check starter-item ${c.in_list ? "in-list" : ""}"><input type="checkbox" data-st="${c.id}" ${c.in_list ? "disabled checked" : chosen.has(c.id) ? "checked" : ""} />
          <span>${esc(es && c.name_es ? c.name_es : c.name)}<small class="muted"> · ${esc(c.pack || c.unit)} · ${esc(zoneLabel(c.zone))}${c.in_list ? " · " + t("in_your_list") : ""}</small></span></label>`).join("")}</fieldset>`).join("") || `<p class="muted">${t("no_results")}</p>`;
      $$("[data-st]", root).forEach((b) => b.addEventListener("change", () => { b.checked ? chosen.add(b.dataset.st) : chosen.delete(b.dataset.st); $("#st-count", root).textContent = `${chosen.size} ${t("selected")}`; }));
      $$("[data-st-all]", root).forEach((b) => b.addEventListener("click", () => {
        $$(`[data-st]`, b.closest("fieldset")).forEach((c) => { if (!c.disabled) { c.checked = true; chosen.add(c.dataset.st); } });
        $("#st-count", root).textContent = `${chosen.size} ${t("selected")}`;
      }));
    };
    $("#st-q", root).addEventListener("input", draw);
    $("#st-cat", root).addEventListener("change", draw);
    $("#st-add", root).addEventListener("click", () => guard("st-error", async () => {
      if (!chosen.size) throw new Error(t("pick_one"));
      const res = await post("/api/catalog/starter/add", { ids: [...chosen] });
      flash("st-ok", `${res.added} ${t("added_no_prices")}`);
      r.items.forEach((c) => { if (chosen.has(c.id)) c.in_list = true; });
      chosen.clear(); $("#st-count", root).textContent = `0 ${t("selected")}`; draw();
      if (after) await after();
    }));
    if (after) $("#st-done", root).addEventListener("click", after);
    draw();
  }

  /* ---------- Catalog extras: search, import, barcode ---------- */
  function wireCatalog() {
    const q = $("#catalog-search");
    if (q) q.addEventListener("input", () => {
      const v = q.value.trim().toLowerCase();
      $$("#catalog-list tbody tr").forEach((tr) => { tr.style.display = !v || tr.textContent.toLowerCase().includes(v) ? "" : "none"; });
    });
    $("#btn-import-items").addEventListener("click", renderImport);
    const scan = $("#btn-scan-barcode");
    if (!("BarcodeDetector" in window)) { scan.title = t("barcode_unsupported"); }
    scan.addEventListener("click", () => scanBarcode($("#item-barcode")));
  }
  function renderImport() {
    const w = $("#import-wrap");
    w.classList.remove("hidden");
    w.innerHTML = `<div class="zone-card"><h3>${t("import_title")}</h3><p class="muted">${t("import_hint")}</p>
      <code class="code-line">name,name_es,category,zone,unit,pack,case_size,par,on_hand,cost,vendor,sku,barcode,aliases,notes</code>
      ${errBox("imp-error")}
      <div class="form-grid cols-2"><div><label for="imp-file">${t("label_csv")}</label><input id="imp-file" type="file" accept=".csv,text/csv" /></div>
      <div><label for="imp-text">${t("import_or_paste")}</label><textarea id="imp-text" rows="3"></textarea></div></div>
      <div class="row"><button type="button" class="btn" id="imp-check">${t("btn_preview")}</button><button type="button" class="btn btn-primary" id="imp-go" disabled>${t("btn_import")}</button>
      <a class="btn btn-ghost" href="/api/items/export.csv">${t("import_template")}</a>
      <button type="button" class="btn btn-ghost" id="imp-close">${t("btn_cancel")}</button></div><div id="imp-result"></div></div>`;
    const getText = async () => { const f = $("#imp-file").files[0]; return f ? await f.text() : $("#imp-text").value; };
    $("#imp-close").addEventListener("click", () => w.classList.add("hidden"));
    $("#imp-check").addEventListener("click", () => guard("imp-error", async () => {
      const r = await post("/api/items/import?dry_run=1", { text: await getText() });
      $("#imp-result").innerHTML = `<p>${r.created} ${t("import_new")} · ${r.updated} ${t("import_updated")}${r.new_vendors.length ? ` · ${t("import_new_vendors")}: ${esc(r.new_vendors.join(", "))}` : ""}</p>
        ${r.errors.length ? `<div class="alert alert-warn">${r.errors.map((e) => `${t("row")} ${e.row}: ${esc(e.error)}`).join("<br>")}</div>` : ""}`;
      $("#imp-go").disabled = !(r.created + r.updated);
    }));
    $("#imp-go").addEventListener("click", () => guard("imp-error", async () => {
      const r = await post("/api/items/import", { text: await getText() });
      $("#imp-result").innerHTML = `<div class="alert alert-ok">${r.created} ${t("import_new")} · ${r.updated} ${t("import_updated")}</div>`;
      $("#imp-go").disabled = true;
      O().refreshView("catalog");
    }));
  }
  async function scanBarcode(input) {
    if (!("BarcodeDetector" in window)) { alert(t("barcode_unsupported")); input.focus(); return; }
    const overlay = document.createElement("div");
    overlay.className = "scan-overlay";
    overlay.innerHTML = `<video playsinline muted></video><button type="button" class="btn btn-primary">${t("btn_cancel")}</button>`;
    document.body.appendChild(overlay);
    let stream = null; let done = false;
    const close = () => { done = true; if (stream) stream.getTracks().forEach((tr) => tr.stop()); overlay.remove(); };
    overlay.querySelector("button").addEventListener("click", close);
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      const v = overlay.querySelector("video"); v.srcObject = stream; await v.play();
      const det = new window.BarcodeDetector();
      const tick = async () => {
        if (done) return;
        try { const codes = await det.detect(v); if (codes.length) { input.value = codes[0].rawValue; close(); return; } } catch (_) { /* keep trying */ }
        requestAnimationFrame(tick);
      };
      tick();
    } catch (e) { close(); alert(e.message); }
  }

  /* ---------- Purchase orders ---------- */
  async function renderOrders() {
    const root = $("#orders-root");
    const [rep, ords] = await Promise.all([api("/api/reorder"), api("/api/orders")]);
    root.innerHTML = card(`<h2>${t("orders_from_list")}</h2>${errBox("po-error")}
      ${rep.groups.length ? `<div class="table-wrap"><table><thead><tr><th>${t("label_vendor")}</th><th>${t("lines")}</th><th>$</th><th></th></tr></thead><tbody>
      ${rep.groups.map((g, i) => `<tr><td>${esc(g.vendor || t("no_vendor"))}</td><td>${g.lines.length}</td><td>${money(g.subtotal)}</td>
        <td><button type="button" class="btn btn-sm btn-primary" data-po-make="${i}">${t("btn_make_po")}</button></td></tr>`).join("")}</tbody></table></div>`
      : `<p class="muted">${t("all_at_par")}</p>`}`) +
      card(`<h2>${t("tab_orders_title")}</h2>
      ${ords.orders.length ? ords.orders.map((p) => `<div class="po-card" data-po="${p.id}">
        <div class="panel-head-row"><h3>${esc(p.number)} · ${esc(p.vendor || t("no_vendor"))} ${O().exBadge(p)}</h3><span class="badge po-${p.status}">${t("po_" + p.status)}</span></div>
        <p class="muted">${when(p.created_at)} · ${p.lines.length} ${t("lines")} · ${money(p.total)}</p>
        <ul class="po-lines">${p.lines.map((l) => `<li>${esc(l.name)} — <b>${l.cases ? `${num(l.cases)} cs (${num(l.qty)} ${esc(l.unit)})` : `${num(l.qty)} ${esc(l.unit)}`}</b>${l.received_qty !== undefined ? ` · ${t("received")} ${num(l.received_qty)}` : ""}</li>`).join("")}</ul>
        ${(p.discrepancies || []).length ? `<div class="alert alert-warn">${t("po_short")}: ${p.discrepancies.map((d) => `${esc(d.name)} ${num(d.received)}/${num(d.ordered)}`).join(", ")}</div>` : ""}
        <div class="row">
          <button type="button" class="btn btn-sm" data-po-copy="${p.id}">📋 ${t("btn_copy")}</button>
          <button type="button" class="btn btn-sm" data-po-mail="${p.id}">✉️ ${t("btn_email_draft")}</button>
          <a class="btn btn-sm" href="/api/orders/${p.id}.csv">CSV</a>
          ${p.status === "draft" ? `<button type="button" class="btn btn-sm" data-po-sent="${p.id}">${t("btn_mark_sent")}</button>` : ""}
          ${p.status !== "received" ? `<button type="button" class="btn btn-sm btn-primary" data-po-recv="${p.id}">${t("btn_receive_po")}</button>
          <button type="button" class="btn btn-sm btn-danger" data-po-del="${p.id}">✕</button>` : ""}
        </div><div class="po-recv"></div></div>`).join("") : `<p class="muted">${t("orders_none")}</p>`}`);
    $$("[data-po-make]", root).forEach((b) => b.addEventListener("click", () => guard("po-error", async () => {
      const g = rep.groups[Number(b.dataset.poMake)];
      await post("/api/orders", { from_reorder: true, vendor_id: g.vendor_id, vendor: g.vendor });
      renderOrders();
    })));
    $$("[data-po-copy]", root).forEach((b) => b.addEventListener("click", async () => {
      const x = await api(`/api/orders/${b.dataset.poCopy}/text`);
      const ok = await copyText(x.subject + "\n\n" + x.body);
      b.textContent = ok ? "✓ " + t("copied") : t("copy_failed");
    }));
    $$("[data-po-mail]", root).forEach((b) => b.addEventListener("click", async () => {
      const x = await api(`/api/orders/${b.dataset.poMail}/text`);
      // Opens the user's own mail app with a draft — nothing is sent by OSFT.
      window.location.href = `mailto:${encodeURIComponent(x.email)}?subject=${encodeURIComponent(x.subject)}&body=${encodeURIComponent(x.body)}`;
    }));
    $$("[data-po-sent]", root).forEach((b) => b.addEventListener("click", () => guard("po-error", async () => { await post(`/api/orders/${b.dataset.poSent}/sent`); renderOrders(); })));
    $$("[data-po-del]", root).forEach((b) => b.addEventListener("click", () => guard("po-error", async () => { if (!confirm(t("confirm_delete"))) return; await del(`/api/orders/${b.dataset.poDel}`); renderOrders(); })));
    $$("[data-po-recv]", root).forEach((b) => b.addEventListener("click", () => {
      const p = ords.orders.find((x) => x.id === b.dataset.poRecv);
      const box = $(".po-recv", b.closest(".po-card"));
      box.innerHTML = `<p class="muted">${t("po_recv_hint")}</p>${p.lines.map((l) => `<div class="row"><span style="flex:1">${esc(l.name)}</span><input type="number" min="0" step="any" data-pr="${l.item_id}" value="${l.qty}" style="width:7rem" /> ${esc(l.unit)}</div>`).join("")}
        <button type="button" class="btn btn-primary btn-sm">${t("btn_confirm_receive")}</button>`;
      $("button", box).addEventListener("click", () => guard("po-error", async () => {
        const received = {}; $$("[data-pr]", box).forEach((i) => (received[i.dataset.pr] = i.value));
        await post(`/api/orders/${p.id}/receive`, { received });
        renderOrders();
      }));
    }));
  }

  /* ---------- Invoice paste / bulk receive ---------- */
  let invItems = [];
  async function renderInvoice() {
    const root = $("#invoice-root");
    invItems = (await api("/api/items")).items || [];
    let vendors = [];
    try { vendors = (await api("/api/vendors")).vendors; } catch (_) { vendors = []; }
    root.innerHTML = card(`<h2>${t("tab_invoice_title")}</h2><p class="muted">${t("invoice_hint")}</p>${errBox("inv-error")}${okBox("inv-ok")}
      <div class="form-grid cols-2">
        <div><label for="inv-vendor">${t("label_vendor")}</label><input id="inv-vendor" list="inv-vendors" /><datalist id="inv-vendors">${vendors.map((v) => `<option value="${esc(v.name)}">`).join("")}</datalist></div>
        <div><label for="inv-no">${t("label_invoice_no")}</label><input id="inv-no" /></div>
        <div style="grid-column:1/-1"><label for="inv-text">${t("invoice_paste")}</label><textarea id="inv-text" rows="5" placeholder="2 cs Ground beef 4.89&#10;3 Ice&#10;12 Corn tortillas 2.29"></textarea></div>
      </div>
      <div class="row"><button type="button" class="btn" id="inv-read">${t("btn_read_lines")}</button><button type="button" class="btn btn-ghost" id="inv-add">+ ${t("btn_add_line")}</button>
      <button type="button" class="btn btn-ghost" data-goto="receive">📷 ${t("invoice_photo_link")}</button></div>
      <div id="inv-lines" class="table-wrap"></div>
      <button type="button" class="btn btn-primary" id="inv-go">${t("btn_receive_all")}</button>`);
    const lines = [];
    const draw = () => {
      $("#inv-lines").innerHTML = lines.length ? `<table><thead><tr><th>${t("invoice_line")}</th><th>${t("label_item")}</th><th>${t("qty")}</th><th>${t("label_unit_cost")}</th><th></th></tr></thead><tbody>
        ${lines.map((l, i) => `<tr><td class="muted">${esc(l.raw || "")}${l.note ? `<div>${esc(l.note)}</div>` : ""}</td>
        <td><select data-il-item="${i}"><option value="">${t("voice_pick_item")}</option>${invItems.map((it) => opt(it.id, `${it.name} (${it.unit})`, it.id === l.item_id)).join("")}</select></td>
        <td><input type="number" min="0" step="any" data-il-qty="${i}" value="${l.qty ?? ""}" /></td>
        <td><input type="number" min="0" step="any" data-il-cost="${i}" value="${l.unit_cost ?? ""}" /></td>
        <td><button type="button" class="btn btn-sm btn-ghost" data-il-del="${i}">✕</button></td></tr>`).join("")}</tbody></table>` : "";
      $$("[data-il-item]").forEach((s) => s.addEventListener("change", () => (lines[s.dataset.ilItem].item_id = s.value)));
      $$("[data-il-qty]").forEach((s) => s.addEventListener("input", () => (lines[s.dataset.ilQty].qty = s.value)));
      $$("[data-il-cost]").forEach((s) => s.addEventListener("input", () => (lines[s.dataset.ilCost].unit_cost = s.value)));
      $$("[data-il-del]").forEach((s) => s.addEventListener("click", () => { lines.splice(Number(s.dataset.ilDel), 1); draw(); }));
    };
    $("#inv-add").addEventListener("click", () => { lines.push({ item_id: "", qty: "", unit_cost: "" }); draw(); });
    $("#inv-read").addEventListener("click", () => guard("inv-error", async () => {
      const r = await post("/api/invoice/parse", { text: $("#inv-text").value });
      r.lines.forEach((l) => lines.push(l)); draw();
    }));
    $("#inv-go").addEventListener("click", () => guard("inv-error", async () => {
      const good = lines.filter((l) => l.item_id && Number(l.qty) > 0);
      if (!good.length) throw new Error(t("pick_one"));
      if (good.length < lines.length && !confirm(t("invoice_skip_unmatched"))) return;
      const r = await post("/api/receives/batch", { vendor: $("#inv-vendor").value, invoice_no: $("#inv-no").value,
        photos: (window.OSFT_V11 && window.OSFT_V11.invoiceFiles) || [],
        lines: good.map((l) => ({ item_id: l.item_id, qty: l.qty, unit_cost: l.unit_cost })) });
      lines.length = 0; draw(); $("#inv-text").value = "";
      flash("inv-ok", `${r.receives.length} ${t("lines_received")}`);
    }));
  }

  /* ---------- Input log ---------- */
  async function renderLog(type = "all") {
    const root = $("#log-root");
    const r = await api(`/api/inputs/log?type=${type}`);
    const types = ["all", "pos", "invoice", "purchase", "po", "transfer"];
    root.innerHTML = card(`<div class="chips">${types.map((x) => `<button type="button" class="chip ${x === type ? "on" : ""}" data-lt="${x}">${t("log_" + x)}</button>`).join("")}</div>
      ${r.rows.length ? `<div class="table-wrap"><table><thead><tr><th>${t("label_date")}</th><th>${t("log_type")}</th><th>${t("log_what")}</th><th>${t("log_by")}</th></tr></thead><tbody>
      ${r.rows.map((x) => `<tr><td class="muted">${when(x.at)}</td><td><span class="badge log-${x.type}">${t("log_" + x.type)}</span></td><td><b>${esc(x.title || "")}</b>${x.example ? O().exBadge(x) : ""}<div class="muted">${esc(x.detail || "")}</div></td><td>${esc(x.by || "—")}</td></tr>`).join("")}
      </tbody></table></div>` : `<p class="muted">${t("log_empty")}</p>`}`);
    $$("[data-lt]", root).forEach((b) => b.addEventListener("click", () => renderLog(b.dataset.lt)));
  }

  /* ---------- Money & stock report ---------- */
  async function renderMoney() {
    const root = $("#money-root");
    const r = await api("/api/reports/summary");
    const m = r.money;
    root.innerHTML = card(`<h2>${t("money_stock")}</h2>
      <div class="metrics-grid"><div class="metric metric--pop metric--wide"><span class="metric-n">${money(r.stock.total_value)}</span><span class="metric-l">${t("m_value")}</span></div>
      <div class="metric metric--teal"><span class="metric-n">${r.stock.item_count}</span><span class="metric-l">${t("m_items")}</span></div>
      <div class="metric ${r.stock.missing_cost ? "metric--hot" : "metric--teal"}"><span class="metric-n">${r.stock.missing_cost}</span><span class="metric-l">${t("missing_cost")}</span></div></div>
      <div class="table-wrap"><table><thead><tr><th>${t("label_category")}</th><th>GL</th><th>${t("m_items")}</th><th>$</th></tr></thead><tbody>
      ${r.stock.by_category.map((c) => `<tr><td>${esc(c.category)}</td><td>${esc(c.gl_code || "—")}</td><td>${c.items}${c.no_cost ? ` <span class="muted">(${c.no_cost} ${t("no_cost")})</span>` : ""}</td><td>${money(c.value)}</td></tr>`).join("")}</tbody></table></div>
      <h3>${t("by_zone")}</h3><div class="chips">${r.stock.by_zone.map((z) => `<span class="chip">${O().zoneBadge(z.zone)} ${money(z.value)}</span>`).join("")}</div>`) +
      card(`<h2>${t("money_cost")}</h2>${m.ready ? `<p class="muted">${esc(m.period[0])} → ${esc(m.period[1])}</p>
      <div class="metrics-grid"><div class="metric metric--orange"><span class="metric-n">${money(m.sales)}</span><span class="metric-l">${t("sales")}</span></div>
      <div class="metric metric--teal"><span class="metric-n">${money(m.cogs)}</span><span class="metric-l">${t("cogs")}</span></div>
      <div class="metric metric--pop"><span class="metric-n">${m.food_cost_pct ?? "—"}%</span><span class="metric-l">${t("food_cost_pct")}</span></div>
      <div class="metric metric--teal"><span class="metric-n">${m.ideal_pct ?? "—"}%</span><span class="metric-l">${t("ideal_pct")}</span></div></div>
      <div class="table-wrap"><table><thead><tr><th>${t("label_category")}</th><th>GL</th><th>${t("cogs")}</th><th>% ${t("sales")}</th><th>${t("target")}</th></tr></thead><tbody>
      ${m.by_category.map((c) => `<tr><td>${esc(c.category)}</td><td>${esc(c.gl_code || "—")}</td><td>${money(c.cogs)}</td><td class="${c.target_pct != null && c.pct_of_sales > c.target_pct ? "neg" : ""}">${c.pct_of_sales ?? "—"}%</td><td>${c.target_pct != null ? c.target_pct + "%" : "—"}</td></tr>`).join("")}</tbody></table></div>`
      : `<p class="muted">${t("money_not_ready")}</p>`}`) +
      card(`<h2>${t("count_history")}</h2>${r.history.length ? `<div class="table-wrap"><table><thead><tr><th>${t("label_date")}</th><th>${t("lines")}</th><th>${t("source")}</th><th>${t("log_by")}</th></tr></thead><tbody>
      ${r.history.map((h) => `<tr><td>${when(h.completed_at)}${O().exBadge(h)}</td><td>${h.lines}</td><td>${t("src_" + h.source)}</td><td>${esc(h.by || "—")}</td></tr>`).join("")}</tbody></table></div>` : `<p class="muted">${t("no_count_yet")}</p>`}`) +
      card(`<h2>${t("exports")}</h2><div class="row">
        <a class="btn" href="/api/export/count.csv">${t("exp_count")}</a><a class="btn" href="/api/export/variance.csv">${t("exp_variance")}</a>
        <a class="btn" href="/api/export/reorder.csv">${t("exp_reorder")}</a><a class="btn" href="/api/export/report.csv">${t("exp_report")}</a>
        <a class="btn" href="/api/items/export.csv">${t("exp_products")}</a></div>`);
  }

  /* ---------- Trucks + transfers ---------- */
  async function renderTrucks() {
    const root = $("#trucks-root");
    const [r, items, tr] = await Promise.all([api("/api/trucks"), api("/api/items"), api("/api/transfers").catch(() => ({ transfers: [] }))]);
    const others = r.trucks.filter((x) => x.id !== r.active_truck_id);
    root.innerHTML = card(`<div class="panel-head-row"><h2>${t("tab_trucks_title")}</h2><span class="caption">${money(r.total_value)}</span></div>${errBox("tr-error")}
      <div class="truck-grid">${r.trucks.map((x) => `<div class="zone-card ${x.id === r.active_truck_id ? "active-truck" : ""}">
        <h3>🚚 ${esc(x.name)}</h3><p class="muted">${x.item_count} ${t("m_items")} · ${money(x.inventory_value)} · ${x.low_par} ${t("low")}</p>
        <p class="muted">${t("last_count")}: ${x.last_count ? when(x.last_count) : "—"}</p>
        <div class="row">${x.id === r.active_truck_id ? `<span class="badge">${t("you_are_here")}</span>` : `<button type="button" class="btn btn-sm btn-primary" data-tk-go="${x.id}">${t("btn_switch")}</button>`}
        <button type="button" class="btn btn-sm" data-tk-ren="${x.id}">${t("btn_rename")}</button>
        ${x.id !== "main" ? `<button type="button" class="btn btn-sm btn-danger" data-tk-del="${x.id}">✕</button>` : ""}</div></div>`).join("")}</div>
      <h3>${t("add_truck")}</h3><form id="tk-form" class="row"><input id="tk-name" placeholder="${esc(t("truck_name_ph"))}" style="flex:1" />
      <label class="check"><input type="checkbox" id="tk-copy" checked /> ${t("copy_products")}</label><button type="submit" class="btn btn-primary">${t("btn_add")}</button></form>`) +
      card(`<h2>${t("transfer_title")}</h2>${others.length ? `<p class="muted">${t("transfer_hint")}</p>
      <div class="form-grid cols-2"><div><label for="xf-to">${t("transfer_to")}</label><select id="xf-to">${others.map((x) => opt(x.id, x.name)).join("")}</select></div>
      <div><label for="xf-note">${t("note")}</label><input id="xf-note" /></div></div>
      <div id="xf-lines"></div><div class="row"><button type="button" class="btn btn-ghost" id="xf-add">+ ${t("btn_add_line")}</button>
      <button type="button" class="btn btn-primary" id="xf-go">${t("btn_transfer")}</button></div>` : `<p class="muted">${t("transfer_need_two")}</p>`}
      ${tr.transfers.length ? `<h3>${t("recent")}</h3><ul>${tr.transfers.slice(0, 10).map((x) => `<li>${when(x.at)} — ${x.direction === "out" ? "→ " + esc(x.to_name) : "← " + esc(x.from_name)}: ${x.lines.map((l) => `${num(l.qty)} ${esc(l.unit)} ${esc(l.name)}`).join(", ")}</li>`).join("")}</ul>` : ""}`);
    $$("[data-tk-go]", root).forEach((b) => b.addEventListener("click", () => guard("tr-error", async () => { await post(`/api/trucks/${b.dataset.tkGo}/activate`); await afterTruckChange(); })));
    $$("[data-tk-ren]", root).forEach((b) => b.addEventListener("click", () => guard("tr-error", async () => {
      const n = prompt(t("truck_name_ph")); if (!n) return; await put(`/api/trucks/${b.dataset.tkRen}`, { name: n }); await afterTruckChange();
    })));
    $$("[data-tk-del]", root).forEach((b) => b.addEventListener("click", () => guard("tr-error", async () => {
      if (!confirm(t("confirm_delete_truck"))) return; await del(`/api/trucks/${b.dataset.tkDel}`); await afterTruckChange();
    })));
    $("#tk-form").addEventListener("submit", (e) => { e.preventDefault(); guard("tr-error", async () => {
      await post("/api/trucks", { name: $("#tk-name").value, copy_products: $("#tk-copy").checked }); await refreshTrucks(); renderTrucks();
    }); });
    if (!others.length) return;
    const addLine = () => {
      const d = document.createElement("div"); d.className = "row xf-line";
      d.innerHTML = `<select class="xf-item" style="flex:1">${items.items.map((i) => opt(i.id, `${i.name} (${num(i.on_hand)} ${i.unit})`)).join("")}</select><input type="number" min="0" step="any" class="xf-qty" style="width:6rem" placeholder="${t("qty")}" /><button type="button" class="btn btn-sm btn-ghost">✕</button>`;
      $("button", d).addEventListener("click", () => d.remove());
      $("#xf-lines").appendChild(d);
    };
    addLine();
    $("#xf-add").addEventListener("click", addLine);
    $("#xf-go").addEventListener("click", () => guard("tr-error", async () => {
      const lines = $$(".xf-line").map((d) => ({ item_id: $(".xf-item", d).value, qty: $(".xf-qty", d).value })).filter((l) => l.qty);
      await post("/api/transfers", { to_truck_id: $("#xf-to").value, lines, note: $("#xf-note").value });
      renderTrucks();
    }));
  }

  /* ---------- Staff board ---------- */
  async function renderBoard() {
    const root = $("#board-root");
    const r = await api("/api/staff-board");
    root.innerHTML = card(`${errBox("bd-error")}<form id="bd-form" class="form-grid"><label for="bd-text">${t("board_new")}</label><textarea id="bd-text" rows="2"></textarea>
      <div class="row"><label class="check"><input type="checkbox" id="bd-pin" /> ${t("board_pin")}</label><label class="check"><input type="checkbox" id="bd-truck" /> ${t("board_this_truck")}</label>
      <button type="submit" class="btn btn-primary">${t("btn_post")}</button></div></form>
      <div class="board">${r.posts.map((p) => `<div class="board-note ${p.pinned ? "pinned" : ""}"><p>${p.pinned ? "📌 " : ""}${esc(p.text)}</p>
        <p class="muted">${esc(p.author || "—")} · ${when(p.created_at)}</p><div class="row"><button type="button" class="btn btn-sm btn-ghost" data-bd-pin="${p.id}">${p.pinned ? t("unpin") : t("pin")}</button>
        <button type="button" class="btn btn-sm btn-ghost" data-bd-del="${p.id}">✕</button></div></div>`).join("") || `<p class="muted">${t("board_empty")}</p>`}</div>`);
    $("#bd-form").addEventListener("submit", (e) => { e.preventDefault(); guard("bd-error", async () => {
      await post("/api/staff-board", { text: $("#bd-text").value, pinned: $("#bd-pin").checked, this_truck_only: $("#bd-truck").checked }); renderBoard();
    }); });
    $$("[data-bd-pin]", root).forEach((b) => b.addEventListener("click", async () => { await post(`/api/staff-board/${b.dataset.bdPin}/pin`); renderBoard(); }));
    $$("[data-bd-del]", root).forEach((b) => b.addEventListener("click", async () => { await del(`/api/staff-board/${b.dataset.bdDel}`); renderBoard(); }));
  }

  /* ---------- People & access ---------- */
  async function renderPeople() {
    const root = $("#people-root");
    let r;
    try { r = await api("/api/people"); } catch (e) { root.innerHTML = card(`<div class="alert alert-warn">${esc(e.message)}</div>`); return; }
    const trucks = (await api("/api/trucks")).trucks;
    if (window.OSFT_V13) { try { await window.OSFT_V13.loadTypes(); } catch (_) {} }
    root.innerHTML = card(`<h2>${t("tab_people_title")}</h2><p class="muted">${t("people_hint")}</p>
      ${!auth.auth_enabled ? `<div class="alert alert-warn">${t("open_mode_long")}</div>` : ""}${errBox("pp-error")}${okBox("pp-ok")}
      <div class="table-wrap"><table><thead><tr><th>${t("label_name")}</th><th>${t("label_login")}</th><th>${t("label_role")}</th><th>PIN</th><th>${t("truck_lock")}</th><th>${t("active")}</th><th></th></tr></thead><tbody>
      ${r.people.map((p) => `<tr><td>${esc(p.name)}</td><td>${esc(p.login)}</td><td>${t("role_" + p.role)}</td><td>${p.has_pin ? "✓" : "—"}</td>
        <td>${esc((trucks.find((x) => x.id === p.truck_id) || {}).name || t("all_trucks"))}</td><td>${p.active ? "✓" : "✕"}</td>
        <td class="row"><button type="button" class="btn btn-sm" data-pp-edit="${p.id}">${t("btn_edit")}</button><button type="button" class="btn btn-sm" data-pp-pin="${p.id}">${t("btn_reset_pin")}</button>
        <button type="button" class="btn btn-sm btn-danger" data-pp-del="${p.id}">✕</button></td></tr>`).join("") || `<tr><td colspan="7" class="muted">${t("people_none")}</td></tr>`}
      </tbody></table></div>
      <button type="button" class="btn btn-primary" id="pp-add">+ ${t("btn_add_person")}</button><div id="pp-form"></div>`);
    const form = (p) => {
      p = p || { role: "crew", permissions: r.defaults.crew, active: true };
      $("#pp-form").innerHTML = `<form id="pp-f" class="form-grid cols-2 zone-card" novalidate><h3 style="grid-column:1/-1">${p.id ? t("btn_edit") + " " + esc(p.name) : t("btn_add_person")}</h3>
        <div><label for="pp-name">${t("label_name")}</label><input id="pp-name" value="${esc(p.name || "")}" /></div>
        <div><label for="pp-login">${t("label_login")}</label><input id="pp-login" value="${esc(p.login || "")}" autocapitalize="off" /></div>
        <div><label for="pp-role">${t("label_role")}</label><select id="pp-role">${r.roles.map((x) => opt(x, t("role_" + x), x === p.role)).join("")}</select></div>
        <div><label for="pp-truck">${t("truck_lock")}</label><select id="pp-truck">${opt("", t("all_trucks"))}${trucks.map((x) => opt(x.id, x.name, x.id === p.truck_id)).join("")}</select></div>
        ${p.id ? "" : `<div><label for="pp-pin">${t("label_pin")}</label><input id="pp-pin" type="password" inputmode="numeric" maxlength="6" class="pin-input" /></div>`}
        <div><label class="check"><input type="checkbox" id="pp-active" ${p.active ? "checked" : ""} /> ${t("active")}</label></div>
        <fieldset style="grid-column:1/-1"><legend>${t("permissions")}</legend><div class="perm-grid">${r.permissions.map((k) => `<label class="check"><input type="checkbox" data-perm="${k}" ${(p.permissions || {})[k] ? "checked" : ""} /> ${t("perm_" + k)}</label>`).join("")}</div></fieldset>
        <fieldset style="grid-column:1/-1" id="pp-ct"><legend>${t("ct_allowed")}</legend><div class="perm-grid">${((window.OSFT_V13 && window.OSFT_V13.types) || []).map((x) => `<label class="check"><input type="checkbox" data-pp-ct="${esc(x.key)}" ${(p.count_types || []).includes(x.key) ? "checked" : ""} /> ${esc(x.name)}</label>`).join("")}</div><small class="muted">${t("ct_allowed_hint")}</small></fieldset>
        <div class="row" style="grid-column:1/-1"><button type="submit" class="btn btn-primary">${t("btn_save")}</button><button type="button" class="btn btn-ghost" id="pp-cancel">${t("btn_cancel")}</button></div></form>`;
      $("#pp-role").addEventListener("change", (e) => { const d = r.defaults[e.target.value]; $$("[data-perm]").forEach((c) => (c.checked = !!d[c.dataset.perm])); });
      $("#pp-cancel").addEventListener("click", () => ($("#pp-form").innerHTML = ""));
      $("#pp-f").addEventListener("submit", (e) => { e.preventDefault(); guard("pp-error", async () => {
        const permissions = {}; $$("[data-perm]").forEach((c) => (permissions[c.dataset.perm] = c.checked));
        const body = { name: $("#pp-name").value, login: $("#pp-login").value, role: $("#pp-role").value, truck_id: $("#pp-truck").value || null, active: $("#pp-active").checked, permissions };
        body.count_types = $$("[data-pp-ct]:checked").map((c) => c.dataset.ppCt);
        if (p.id) await put(`/api/people/${p.id}`, body); else await post("/api/people", { ...body, pin: $("#pp-pin").value });
        await refreshAuth(); renderPeople();
      }); });
    };
    $("#pp-add").addEventListener("click", () => form(null));
    $$("[data-pp-edit]", root).forEach((b) => b.addEventListener("click", () => form(r.people.find((p) => p.id === b.dataset.ppEdit))));
    $$("[data-pp-pin]", root).forEach((b) => b.addEventListener("click", () => guard("pp-error", async () => {
      const pin = prompt(t("new_pin_prompt")); if (!pin) return;
      await post(`/api/people/${b.dataset.ppPin}/reset-pin`, { pin }); flash("pp-ok", t("saved")); await refreshAuth(); renderPeople();
    })));
    $$("[data-pp-del]", root).forEach((b) => b.addEventListener("click", () => guard("pp-error", async () => {
      if (!confirm(t("confirm_delete"))) return; await del(`/api/people/${b.dataset.ppDel}`); await refreshAuth(); renderPeople();
    })));
  }

  /* ---------- Vendors ---------- */
  const VF = ["name", "rep", "phone", "email", "account_no", "cutoff", "delivery_days", "lead_days", "terms", "order_method", "notes"];
  async function renderVendors() {
    const root = $("#vendors-root");
    const r = await api("/api/vendors");
    root.innerHTML = card(`<h2>${t("tab_vendors_title")}</h2>${errBox("vd-error")}
      <div class="table-wrap"><table><thead><tr><th>${t("vf_name")}</th><th>${t("vf_rep")}</th><th>${t("vf_phone")}</th><th>${t("vf_account_no")}</th><th>${t("vf_cutoff")}</th><th>${t("vf_delivery_days")}</th><th></th></tr></thead><tbody>
      ${r.vendors.map((v) => `<tr><td><b>${esc(v.name)}</b>${O().exBadge(v)}<div class="muted">${esc(v.email || "")}</div></td><td>${esc(v.rep || "")}</td><td>${v.phone ? `<a href="tel:${esc(v.phone)}">${esc(v.phone)}</a>` : ""}</td><td>${esc(v.account_no || "")}</td><td>${esc(v.cutoff || "")}</td><td>${esc(v.delivery_days || "")}</td>
        <td class="row"><button type="button" class="btn btn-sm" data-vd-edit="${v.id}">${t("btn_edit")}</button><button type="button" class="btn btn-sm btn-danger" data-vd-del="${v.id}">✕</button></td></tr>`).join("") || `<tr><td colspan="7" class="muted">${t("vendors_none")}</td></tr>`}
      </tbody></table></div><button type="button" class="btn btn-primary" id="vd-add">+ ${t("btn_add_vendor")}</button><div id="vd-form"></div>`);
    const form = (v) => {
      v = v || {};
      $("#vd-form").innerHTML = `<form id="vd-f" class="form-grid cols-2 zone-card" novalidate>${VF.map((k) => `<div ${k === "notes" ? 'style="grid-column:1/-1"' : ""}><label for="vf-${k}">${t("vf_" + k)}</label><input id="vf-${k}" value="${esc(v[k] || "")}" ${k === "email" ? 'type="email"' : k === "phone" ? 'type="tel"' : ""} /></div>`).join("")}
        <div class="row" style="grid-column:1/-1"><button type="submit" class="btn btn-primary">${t("btn_save")}</button><button type="button" class="btn btn-ghost" id="vd-cancel">${t("btn_cancel")}</button></div></form>`;
      $("#vd-cancel").addEventListener("click", () => ($("#vd-form").innerHTML = ""));
      $("#vd-f").addEventListener("submit", (e) => { e.preventDefault(); guard("vd-error", async () => {
        const body = {}; VF.forEach((k) => (body[k] = $("#vf-" + k).value));
        if (v.id) await put(`/api/vendors/${v.id}`, body); else await post("/api/vendors", body);
        renderVendors();
      }); });
    };
    $("#vd-add").addEventListener("click", () => form(null));
    $$("[data-vd-edit]", root).forEach((b) => b.addEventListener("click", () => form(r.vendors.find((v) => v.id === b.dataset.vdEdit))));
    $$("[data-vd-del]", root).forEach((b) => b.addEventListener("click", () => guard("vd-error", async () => { if (!confirm(t("confirm_delete"))) return; await del(`/api/vendors/${b.dataset.vdDel}`); renderVendors(); })));
  }

  /* ---------- Categories (GL) + POS accounts ---------- */
  async function renderAccounts() {
    const root = $("#accounts-root");
    const [c, p, ad] = await Promise.all([api("/api/accounts/categories"), api("/api/accounts/pos"), api("/api/pos/adapters")]);
    root.innerHTML = card(`<h2>${t("categories_title")}</h2><p class="muted">${t("categories_hint")}</p>${errBox("ac-error")}${okBox("ac-ok")}
      <div class="table-wrap"><table><thead><tr><th>${t("label_category")}</th><th>${t("gl_code")}</th><th>${t("kind")}</th><th>${t("target")} %</th><th></th></tr></thead><tbody>
      ${c.categories.map((x) => `<tr data-cat="${x.id}"><td><input class="c-name" value="${esc(x.name)}" /></td><td><input class="c-gl" value="${esc(x.gl_code || "")}" size="8" /></td>
        <td><select class="c-kind">${c.kinds.map((k) => opt(k, t("kind_" + k), k === x.kind)).join("")}</select></td>
        <td><input class="c-tp" type="number" min="0" max="100" step="any" value="${x.target_pct ?? ""}" style="width:5rem" /></td>
        <td class="row"><button type="button" class="btn btn-sm" data-c-save="${x.id}">${t("btn_save")}</button><button type="button" class="btn btn-sm btn-ghost" data-c-del="${x.id}">✕</button></td></tr>`).join("")}</tbody></table></div>
      <form id="c-add" class="row"><input id="c-new" placeholder="${esc(t("new_category"))}" style="flex:1" /><button type="submit" class="btn btn-primary">${t("btn_add")}</button></form>`) +
      card(`<h2>${t("pos_accounts_title")}</h2><p class="muted">${t("pos_accounts_hint")}</p>
      <ul class="pos-acc">${p.pos_accounts.map((a) => `<li><b>${esc(a.label)}</b> · ${esc((ad.adapters.find((x) => x.key === a.provider) || {}).label || a.provider)}${a.location ? " · " + esc(a.location) : ""}${a.default ? ` <span class="badge">${t("default")}</span>` : ""}${O().exBadge(a)}
        <button type="button" class="btn btn-sm btn-ghost" data-pa-def="${a.id}">${t("make_default")}</button><button type="button" class="btn btn-sm btn-ghost" data-pa-del="${a.id}">✕</button></li>`).join("") || `<li class="muted">${t("pos_accounts_none")}</li>`}</ul>
      <form id="pa-add" class="form-grid cols-2"><div><label for="pa-label">${t("label_name")}</label><input id="pa-label" placeholder="Square — truck 1" /></div>
      <div><label for="pa-prov">${t("label_pos")}</label><select id="pa-prov">${ad.adapters.map((a) => opt(a.key, a.label)).join("")}</select></div>
      <div><label for="pa-loc">${t("label_location")}</label><input id="pa-loc" /></div><div><label for="pa-ref">${t("label_account_ref")}</label><input id="pa-ref" /></div>
      <div><button type="submit" class="btn btn-primary">${t("btn_add")}</button></div></form>`);
    $$("[data-c-save]", root).forEach((b) => b.addEventListener("click", () => guard("ac-error", async () => {
      const tr = b.closest("tr");
      await put(`/api/accounts/categories/${b.dataset.cSave}`, { name: $(".c-name", tr).value, gl_code: $(".c-gl", tr).value, kind: $(".c-kind", tr).value, target_pct: $(".c-tp", tr).value });
      flash("ac-ok", t("saved"));
    })));
    $$("[data-c-del]", root).forEach((b) => b.addEventListener("click", () => guard("ac-error", async () => { await del(`/api/accounts/categories/${b.dataset.cDel}`); renderAccounts(); })));
    $("#c-add").addEventListener("submit", (e) => { e.preventDefault(); guard("ac-error", async () => { await post("/api/accounts/categories", { name: $("#c-new").value }); renderAccounts(); }); });
    $$("[data-pa-def]", root).forEach((b) => b.addEventListener("click", () => guard("ac-error", async () => { await put(`/api/accounts/pos/${b.dataset.paDef}`, { default: true }); renderAccounts(); })));
    $$("[data-pa-del]", root).forEach((b) => b.addEventListener("click", () => guard("ac-error", async () => { await del(`/api/accounts/pos/${b.dataset.paDel}`); renderAccounts(); })));
    $("#pa-add").addEventListener("submit", (e) => { e.preventDefault(); guard("ac-error", async () => {
      await post("/api/accounts/pos", { label: $("#pa-label").value, provider: $("#pa-prov").value, location: $("#pa-loc").value, account_ref: $("#pa-ref").value }); renderAccounts();
    }); });
  }

  /* ---------- Business profile (top of Settings) + zones ---------- */
  async function renderBusiness() {
    const root = $("#business-root");
    if (!root) return;
    const b = (await api("/api/business")).business;
    business = b;
    root.innerHTML = card(`<h2>${t("business_title")}</h2>${errBox("bz-error")}${okBox("bz-ok")}
      <form id="bz-f" class="form-grid cols-2" novalidate>
        <div><label for="bz-name">${t("label_business_name")}</label><input id="bz-name" value="${esc(b.name)}" /></div>
        <div><label for="bz-legal">${t("label_legal_name")}</label><input id="bz-legal" value="${esc(b.legal_name)}" /></div>
        <div style="grid-column:1/-1"><label for="bz-address">${t("label_address")}</label><input id="bz-address" value="${esc(b.address)}" /></div>
        <div><label for="bz-phone">${t("label_phone")}</label><input id="bz-phone" type="tel" value="${esc(b.phone)}" /></div>
        <div><label for="bz-email">${t("label_email")}</label><input id="bz-email" type="email" value="${esc(b.email)}" /></div>
        <div><label for="bz-web">${t("label_website")}</label><input id="bz-web" value="${esc(b.website)}" /></div>
        <div><label for="bz-tz">${t("label_timezone")}</label><input id="bz-tz" value="${esc(b.timezone)}" /></div>
        <div><label for="bz-cycle">${t("label_cycle_days")}</label><input id="bz-cycle" type="number" min="1" max="31" value="${esc(b.cycle_days)}" /></div>
        <div><label for="bz-anchor">${t("label_week_start")}</label><select id="bz-anchor">${["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].map((d) => opt(d, t("day_" + d), d === b.anchor_day)).join("")}</select></div>
        <div style="grid-column:1/-1"><label for="bz-logo">${t("label_logo")}</label><div class="row">${b.logo_data_url ? `<img src="${esc(b.logo_data_url)}" alt="" class="logo-prev" />` : ""}<input id="bz-logo" type="file" accept="image/*" />
          ${b.logo_data_url ? `<button type="button" class="btn btn-sm btn-ghost" id="bz-logo-rm">${t("remove")}</button>` : ""}</div></div>
        <div class="row" style="grid-column:1/-1"><button type="submit" class="btn btn-primary">${t("btn_save")}</button>
        <button type="button" class="btn btn-ghost" id="bz-rerun">${t("rerun_setup")}</button></div>
      </form>
      <h3>${t("tab_sections_title")}</h3><p class="muted">${t("sec_hint")}</p>
      <button type="button" class="btn" id="bz-sections">🗺️ ${t("tab_sections_title")} →</button>`);
    const readLogo = () => new Promise((res, rej) => {
      const f = $("#bz-logo").files[0]; if (!f) return res(undefined);
      if (f.size > 300000) return rej(new Error(t("logo_too_big")));
      const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = rej; fr.readAsDataURL(f);
    });
    $("#bz-f").addEventListener("submit", (e) => { e.preventDefault(); guard("bz-error", async () => {
      const logo = await readLogo();
      const body = { name: $("#bz-name").value, legal_name: $("#bz-legal").value, address: $("#bz-address").value, phone: $("#bz-phone").value,
        email: $("#bz-email").value, website: $("#bz-web").value, timezone: $("#bz-tz").value, cycle_days: $("#bz-cycle").value, anchor_day: $("#bz-anchor").value };
      if (logo !== undefined) body.logo_data_url = logo;
      await put("/api/business", body); flash("bz-ok", t("saved")); renderBusiness(); applyLogo();
    }); });
    const rm = $("#bz-logo-rm"); if (rm) rm.addEventListener("click", () => guard("bz-error", async () => { await put("/api/business", { logo_data_url: "" }); renderBusiness(); applyLogo(); }));
    $("#bz-rerun").addEventListener("click", () => guard("bz-error", async () => { if (!confirm(t("rerun_confirm"))) return; ob = await put("/api/onboarding", { phase: "welcome" }); O().showView("onboarding"); }));
    $("#bz-sections").addEventListener("click", () => O().showView("sections"));
  }
  async function applyLogo() {
    try {
      const b = (await api("/api/business")).business;
      business = b;
      const mark = $(".sidebar-mark img");
      if (mark) { if (b.logo_data_url) { mark.src = b.logo_data_url; mark.classList.remove("spin"); } else { mark.src = "/static/img/gear.svg"; mark.classList.add("spin"); } }
    } catch (_) { /* not logged in */ }
  }

  /* ---------- Backups & data ---------- */
  async function renderData() {
    const root = $("#data-root");
    const r = await api("/api/backups");
    root.innerHTML = card(`<h2>${t("backups_title")}</h2><p class="muted">${t("backups_hint")}</p>${errBox("dt-error")}${okBox("dt-ok")}
      <div class="row"><button type="button" class="btn btn-primary" id="dt-now">${t("btn_backup_now")}</button><a class="btn" href="/api/backup">⬇ ${t("btn_download_backup")}</a></div>
      <ul class="backup-list">${r.backups.slice(0, 10).map((b) => `<li>${esc(b.name)} <span class="muted">${when(b.at)} · ${Math.ceil(b.size / 1024)} KB</span></li>`).join("") || `<li class="muted">${t("backups_none")}</li>`}</ul>
      <h3>${t("restore_title")}</h3><p class="muted">${t("restore_hint")}</p>
      <div class="row"><input type="file" id="dt-file" accept=".zip,.json" /><button type="button" class="btn" id="dt-restore">${t("btn_restore")}</button></div>`) +
      card(`<h2>${t("sample_title")}</h2><p class="muted">${t("sample_hint")}</p><button type="button" class="btn" id="dt-sample">🌮 ${t("ob_sample")}</button>`) +
      card(`<h2 class="neg">${t("danger_zone")}</h2><p class="muted">${t("reset_truck_hint")}</p><button type="button" class="btn btn-danger" id="dt-reset">${t("btn_reset_truck")}</button>
      <p class="muted" style="margin-top:1rem">${t("reset_all_hint")}</p><div class="row"><input id="dt-confirm" placeholder="RESET" style="width:8rem" /><button type="button" class="btn btn-danger" id="dt-reset-all">${t("btn_reset_all")}</button></div>`);
    $("#dt-now").addEventListener("click", () => guard("dt-error", async () => { await post("/api/backups"); renderData(); }));
    $("#dt-restore").addEventListener("click", () => guard("dt-error", async () => {
      const f = $("#dt-file").files[0]; if (!f) throw new Error(t("pick_file"));
      if (!confirm(t("restore_confirm"))) return;
      const fd = new FormData(); fd.append("file", f); await O().apiForm("/api/restore", fd); location.reload();
    }));
    $("#dt-sample").addEventListener("click", () => guard("dt-error", async () => { if (!confirm(t("confirm_seed"))) return; await post("/api/onboarding/sample"); await finishOnboarding(); }));
    $("#dt-reset").addEventListener("click", () => guard("dt-error", async () => { if (!confirm(t("reset_confirm"))) return; await post("/api/reset"); flash("dt-ok", t("reset_done")); }));
    $("#dt-reset-all").addEventListener("click", () => guard("dt-error", async () => { await post("/api/reset/all", { confirm: $("#dt-confirm").value }); location.reload(); }));
  }

  /* ---------- Placeholder translation for inputs ---------- */
  function applyPlaceholders() { $$("[data-i18n-ph]").forEach((el) => { const v = t(el.dataset.i18nPh); if (v !== el.dataset.i18nPh) el.placeholder = v; }); }

  /* ---------- Boot ---------- */
  async function boot(obInfo) {
    const R = O().registerView;
    R("voice", renderVoice); R("starter", () => renderStarter()); R("orders", renderOrders); R("invoice", async () => { await renderInvoice(); await window.OSFT_V11.enhanceInvoice(); });
    R("log", () => renderLog()); R("money", renderMoney); R("trucks", renderTrucks); R("board", renderBoard);
    R("people", renderPeople); R("vendors", renderVendors); R("accounts", renderAccounts); R("data", renderData);
    R("setup", renderBusiness); R("onboarding", () => window.OSFT_V11.renderOnboarding(true));
    R("sections", () => window.OSFT_V11.renderSectionsView()); R("ai", () => window.OSFT_V11.renderAIView()); R("login", renderLogin);
    R("home", () => { document.body.classList.remove("focus-mode"); return refreshTrucks(); });
    O().onLoginRequired = () => { if (O().currentView !== "login") O().showView("login"); };
    wireCatalog();
    applyPlaceholders();
    $$(".locale-switch button").forEach((b) => b.addEventListener("click", () => setTimeout(applyPlaceholders, 300)));
    business = obInfo.business || {};
    auth = obInfo.auth || auth;
    await refreshAuth();
    if (!(auth.auth_enabled && !auth.user)) await O().syncZones();
    if (!obInfo.onboarding.completed) { window.OSFT_V11.prime(obInfo); return O().showView("onboarding"); }
    if (auth.auth_enabled && !auth.user) return O().showView("login");
    await applyLogo();
    O().showView("home");
  }

  window.OSFT_V1 = { attachMic, micBlock, renderStarter, finishOnboarding, refreshAuth, card, errBox, okBox, flash, hide, guard, opt, can, SR };
  window.OSFT = Object.assign(window.OSFT || {}, {
    boot,
    simulateTranscript(text) { const ta = document.getElementById("voice-text"); if (ta) { ta.value = text; return checkVoice(); } return null; },
  });
})();
