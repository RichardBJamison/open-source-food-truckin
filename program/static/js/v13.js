/* OSFT v1.3 — count types (daily end-of-shift partial, weekly full, monthly in-depth), scoped count walk,
   count history (type · scope · who), Settings › Count types. Mirrors OSBW's count cycle + station-scoped counts:
   a partial count only answers for what it covers; everything else keeps its last known on-hand. */
(function () {
  "use strict";
  const O = () => window.OSFT;
  const V = () => window.OSFT_V1;
  const t = (k) => O().t(k);
  const esc = (s) => O().esc(s);
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const api = (p, o) => O().api(p, o);
  const es = () => O().locale === "es";
  let types = [], cats = [], current = null;
  const tname = (x) => (es() && x.name_es) || x.name;
  const tf = (k, o) => Object.entries(o).reduce((s, [a, b]) => s.replace("{" + a + "}", b), t(k));

  async function loadTypes() {
    const r = await api("/api/count-types");
    types = r.count_types || []; cats = r.categories || [];
    return types;
  }

  function scopeItems(items, sess) {
    const sc = (sess && sess.scope) || null;
    if (!sc || sc.full !== false) return items;
    const ids = new Set(sc.item_ids || []);
    return items.filter((i) => ids.has(i.id));
  }

  async function countChrome(inProg) {
    current = inProg || null;
    try { await loadTypes(); } catch (_) { types = []; }
    const sel = $("#count-type"), date = $("#count-date"), start = $("#btn-start-count");
    const usable = types.filter((x) => x.enabled !== false && x.allowed !== false);
    if (sel) {
      const prev = sel.value;
      sel.innerHTML = usable.map((x) => `<option value="${esc(x.key)}">${esc(tname(x))} · ${x.item_count}</option>`).join("");
      if (prev && usable.some((x) => x.key === prev)) sel.value = prev;
      else if (usable.some((x) => x.key === "weekly")) sel.value = "weekly";
      sel.disabled = !!inProg || !usable.length;
    }
    if (date) { if (!date.value) date.value = O().todayISO ? O().todayISO() : new Date().toISOString().slice(0, 10); date.disabled = !!inProg; }
    if (start) start.disabled = !usable.length;
    const box = $("#count-scope"), cl = $("#count-checklist");
    if (inProg && inProg.scope) {
      const sc = inProg.scope;
      box.className = "alert " + (sc.full === false ? "alert-info ct-partial" : "alert-ok");
      box.innerHTML = `<strong>${esc(inProg.type_name || t("ct_full"))}</strong> · ${esc(inProg.business_date || "")} · ${t(inProg.timing === "end_of_shift" ? "ct_eos" : "ct_bs")}<br>
        ${esc(sc.label || "")} — ${sc.full === false ? tf("ct_partial_note", { n: (sc.item_ids || []).length }) : t("ct_full_note")}`;
      cl.innerHTML = (sc.checklist || []).length ? `<fieldset class="zone-card ct-checklist"><legend>${t("ct_extras")}</legend>${sc.checklist.map((c) =>
        `<label class="check"><input type="checkbox" data-ct-check="${esc(c)}" ${(inProg.checklist_done || {})[c] ? "checked" : ""}/> ${esc(c)}</label>`).join("")}</fieldset>` : "";
    } else {
      const k = sel && sel.value, x = types.find((y) => y.key === k);
      box.className = x ? "muted ct-hint" : "hidden";
      box.innerHTML = x ? `${t("ct_will_cover")}: ${esc(x.scope_label)} (${x.item_count})${x.full ? "" : " — " + t("ct_partial_short")}` : "";
      cl.innerHTML = "";
      if (sel && !sel.dataset.wired) { sel.dataset.wired = "1"; sel.addEventListener("change", () => countChrome(null)); }
    }
    if (window.OSFT_V13.lastSummary && !inProg) {
      const s = window.OSFT_V13.lastSummary.summary || {};
      box.insertAdjacentHTML("afterbegin", `<div class="alert alert-ok ct-done">${tf("ct_done", { n: s.counted || 0 })}${s.not_counted_kept ? " · " + tf("ct_kept", { n: s.not_counted_kept }) : ""}${(s.missing_in_scope || []).length ? " · " + tf("ct_missing", { n: s.missing_in_scope.length }) : ""}</div>`);
      box.className = "";
      window.OSFT_V13.lastSummary = null;
    }
    await renderHistory();
  }

  function startBody() {
    return { type: ($("#count-type") || {}).value || "weekly", date: ($("#count-date") || {}).value || undefined };
  }
  function checklistBody() {
    const boxes = $$("[data-ct-check]");
    if (!boxes.length) return {};
    const done = {}; boxes.forEach((b) => (done[b.dataset.ctCheck] = b.checked));
    return { checklist_done: done };
  }

  async function renderHistory() {
    const el = $("#count-history"); if (!el) return;
    let r; try { r = await api("/api/counts/history"); } catch (e) { el.innerHTML = `<p class="muted">${esc(e.message)}</p>`; return; }
    const rows = r.history || [];
    el.innerHTML = rows.length ? `<table class="ct-history"><thead><tr><th>${t("label_date")}</th><th>${t("ct_type")}</th><th>${t("ct_scope")}</th><th>${t("ct_by")}</th><th>${t("ct_lines")}</th><th></th></tr></thead><tbody>
      ${rows.slice(0, 30).map((h) => `<tr data-ct-hist="${esc(h.type)}"><td>${esc(h.business_date)}</td>
        <td><span class="pill ${h.full ? "" : "pill-partial"}">${esc(h.type_name)}</span></td>
        <td>${esc(h.scope_label)}</td><td>${esc(h.by || "—")}</td><td>${h.lines}${h.in_scope ? " / " + h.in_scope : ""}</td>
        <td class="muted">${h.summary && (h.summary.missing_in_scope || []).length ? "⚠ " + tf("ct_missing", { n: h.summary.missing_in_scope.length }) : ""}</td></tr>`).join("")}
      </tbody></table>` : `<p class="muted">${t("no_counts_start")}</p>`;
  }

  /* ---------- Settings › Count types ---------- */
  async function renderSettings() {
    const root = $("#counttypes-root"); if (!root) return;
    await loadTypes();
    const secs = (await api("/api/sections")).sections || [];
    const items = (await api("/api/items")).items || [];
    const draw = () => {
      root.innerHTML = V().card(`<h2>${t("ct_title")}</h2><p class="muted">${t("ct_settings_hint")}</p>${V().errBox("ct-error")}${V().okBox("ct-ok")}
        ${types.map((x, n) => `<fieldset class="zone-card ct-type" data-ct="${n}"><legend><input class="ct-name" data-f="name" value="${esc(x.name)}" aria-label="${t("label_name")}"/></legend>
          <div class="form-grid cols-2">
            <label class="check"><input type="checkbox" data-f="enabled" ${x.enabled !== false ? "checked" : ""}/> ${t("active")}</label>
            <label class="check"><input type="checkbox" data-f="full" ${x.full ? "checked" : ""}/> ${t("ct_is_full")}</label>
            <div><label>${t("ct_timing")}</label><select data-f="timing">${["before_service", "end_of_shift"].map((v) => V().opt(v, t(v === "end_of_shift" ? "ct_eos" : "ct_bs"), x.timing === v)).join("")}</select></div>
            <div><label>${t("ct_every")}</label><input type="number" min="1" max="92" data-f="interval_days" value="${x.interval_days || 7}"/></div>
          </div>
          <div class="ct-scope-edit ${x.full ? "hidden" : ""}">
            <p class="muted">${t("ct_scope_pick")}</p>
            <div class="perm-grid">${secs.map((s) => `<label class="check"><input type="checkbox" data-sec="${esc(s.key)}" ${(x.sections || []).includes(s.key) ? "checked" : ""}/> ${esc(s.name)}</label>`).join("")}</div>
            <p class="muted">${t("ct_categories")}</p>
            <div class="perm-grid">${[...new Set([...cats, ...(x.categories || [])])].map((c) => `<label class="check"><input type="checkbox" data-cat="${esc(c)}" ${(x.categories || []).map((y) => y.toLowerCase()).includes(c.toLowerCase()) ? "checked" : ""}/> ${esc(c)}</label>`).join("")}</div>
            <details><summary>${t("ct_watch")} (${(x.items || []).length})</summary><div class="perm-grid">${items.map((i) => `<label class="check"><input type="checkbox" data-item="${i.id}" ${(x.items || []).includes(i.id) ? "checked" : ""}/> ${esc(i.name)}</label>`).join("")}</div></details>
          </div>
          <div class="ct-full-edit ${x.full ? "" : "hidden"}">
            <p class="muted">${t("ct_exclude")}</p>
            <div class="perm-grid">${secs.map((s) => `<label class="check"><input type="checkbox" data-ex="${esc(s.key)}" ${(x.exclude_sections || []).includes(s.key) ? "checked" : ""}/> ${esc(s.name)}</label>`).join("")}</div>
            <label>${t("ct_extras")}</label><textarea data-f="checklist" rows="2" placeholder="Propane, Waste review">${esc((x.checklist || []).join(", "))}</textarea>
          </div>
          <p class="muted">${t("ct_will_cover")}: ${esc(x.scope_label || "")} (${x.item_count ?? "?"})</p>
        </fieldset>`).join("")}
        <div class="row"><button type="button" class="btn btn-primary" id="ct-save">${t("btn_save")}</button></div>`);
      $$("[data-f=full]", root).forEach((c) => c.addEventListener("change", () => {
        const fs = c.closest("[data-ct]"); $(".ct-scope-edit", fs).classList.toggle("hidden", c.checked); $(".ct-full-edit", fs).classList.toggle("hidden", !c.checked);
      }));
      $("#ct-save").addEventListener("click", () => V().guard("ct-error", async () => {
        const body = $$("[data-ct]", root).map((fs) => {
          const x = types[+fs.dataset.ct], g = (f) => $(`[data-f=${f}]`, fs);
          return { ...x, name: g("name").value, enabled: g("enabled").checked, full: g("full").checked, timing: g("timing").value,
            interval_days: +g("interval_days").value || 7,
            sections: $$("[data-sec]:checked", fs).map((c) => c.dataset.sec), categories: $$("[data-cat]:checked", fs).map((c) => c.dataset.cat),
            items: $$("[data-item]:checked", fs).map((c) => c.dataset.item), exclude_sections: $$("[data-ex]:checked", fs).map((c) => c.dataset.ex),
            checklist: g("checklist").value.split(/[,\n]/).map((s) => s.trim()).filter(Boolean) };
        });
        const r = await api("/api/count-types", { method: "PUT", body: JSON.stringify({ count_types: body }) });
        types = r.count_types; draw(); V().flash("ct-ok", t("saved"));
      }));
    };
    draw();
  }

  function register() {
    if (!O() || !O().registerView) return setTimeout(register, 30);
    O().registerView("counttypes", renderSettings);
  }
  window.OSFT_V13 = { scopeItems, countChrome, startBody, checklistBody, renderHistory, renderSettings, loadTypes, lastSummary: null,
    get types() { return types; } };
  register();
})();
