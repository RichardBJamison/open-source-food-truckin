/* OSFT front-end — local-first inventory UI */
(function () {
  "use strict";

  let ZONES = ["cooler", "freezer", "dry", "prep"];
  const extraViews = {};
  let strings = {};
  let locale = "en";
  let settings = {};
  let items = [];
  let activeCountId = null;
  let currentView = "home";

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  function t(key) {
    return strings[key] || key;
  }

  function applyI18n() {
    $$("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (strings[key]) el.textContent = strings[key];
    });
    $$("[data-i18n-html]").forEach((el) => { const k = el.getAttribute("data-i18n-html"); if (strings[k]) el.innerHTML = strings[k]; }); // own locale strings only
    $$("[data-i18n-ph]").forEach((el) => { const k = el.getAttribute("data-i18n-ph"); if (strings[k]) el.placeholder = strings[k]; });
    document.documentElement.lang = locale;
    if (typeof renderTabs === "function") renderTabs();
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      ...opts,
    });
    let body = null;
    try {
      body = await res.json();
    } catch (_) {
      body = { ok: false, error: "Invalid JSON response" };
    }
    if (!res.ok) {
      if (res.status === 401 && body && body.login_required && window.OSFT && window.OSFT.onLoginRequired) window.OSFT.onLoginRequired();
      const msg = (body && body.error) || `HTTP ${res.status}`;
      const err = new Error(msg);
      err.status = res.status;
      err.body = body;
      throw err;
    }
    return body;
  }

  function showErr(el, msg) {
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
  }
  function hideErr(el) {
    if (!el) return;
    el.classList.add("hidden");
    el.textContent = "";
  }

  let SECNAMES = {};
  const LEGACY_SEC = { cooler: "Cooler", freezer: "Freezer", dry: "Dry storage", prep: "Prep", outside: "Outside", window: "Window", commissary: "Commissary" };
  function zoneName(z) {
    const n = SECNAMES[z];
    const tr = strings["zone_" + z];
    if (!n) return tr || z;
    if (tr && LEGACY_SEC[z] === n) return tr;
    return n;
  }
  function zoneBadge(zone) {
    return `<span class="badge badge-${esc(zone)}">${esc(zoneName(zone))}</span>`;
  }

  function fmtNum(n) {
    if (n === null || n === undefined) return "—";
    const x = Number(n);
    return Number.isInteger(x) ? String(x) : x.toFixed(2).replace(/\.?0+$/, "");
  }

  /* ----- Views ----- */
  /* ----- Layout: OSBW-style sidebar groups + workbook tabs ----- */
  const GROUPS = {
    home: ["home"],
    sheets: ["count", "voice", "variance", "reorder", "orders", "catalog", "starter"],
    reports: ["reports", "money"],
    inhouse: ["zones", "trucks", "board"],
    inputs: ["log", "sales", "receive", "invoice"],
    menu: ["menu"],
    stops: ["stops"],
    setup: ["setup", "sections", "counttypes", "ai", "people", "vendors", "accounts", "data", "library"],
    onboarding: ["onboarding"],
    login: ["login"],
  };
  const TAB_LABEL = {
    count: ["tab_count", "📱"], voice: ["tab_voice", "🎙️"], variance: ["tab_variance", "⚖️"], reorder: ["tab_reorder", "🛒"],
    orders: ["tab_orders", "📨"], catalog: ["tab_catalog", "🗂️"], starter: ["tab_starter", "📚"],
    sales: ["tab_sales", "🔌"], receive: ["tab_receive", "🧾"], invoice: ["tab_invoice", "📄"], log: ["tab_log", "🗒️"],
    reports: ["tab_var_sales", "📉"], money: ["tab_money", "💵"],
    zones: ["tab_zones", "🧊"], trucks: ["tab_trucks", "🚚"], board: ["tab_board", "📌"],
    setup: ["tab_business", "🏪"], sections: ["tab_sections", "🗺️"], counttypes: ["tab_counttypes", "🗓️"], ai: ["tab_ai", "✨"], people: ["tab_people", "👥"], vendors: ["tab_vendors", "🤝"],
    accounts: ["tab_accounts", "🏷️"], data: ["tab_data", "💾"], library: ["tab_library", "📖"],
  };
  function groupOf(view) {
    return Object.keys(GROUPS).find((g) => GROUPS[g].includes(view)) || "home";
  }
  function renderTabs() {
    $$(".workbook-tabs[data-tabs]").forEach((bar) => {
      const g = bar.dataset.tabs;
      if (!GROUPS[g] || GROUPS[g].length < 2) { bar.innerHTML = ""; return; }
      bar.innerHTML = GROUPS[g].map((v) =>
        `<button type="button" role="tab" class="workbook-tab" data-tab="${v}" aria-selected="false"><span aria-hidden="true">${TAB_LABEL[v][1]}</span> ${esc(t(TAB_LABEL[v][0]))}</button>`).join("");
    });
    markTabs();
  }
  function markTabs() {
    $$(".workbook-tab").forEach((b) => {
      const on = b.dataset.tab === currentView;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
  }
  function setDrawer(open) {
    document.body.classList.toggle("drawer-open", open);
    $("#menu-toggle").setAttribute("aria-expanded", open ? "true" : "false");
    $("#scrim").hidden = !open;
  }
  function showView(name) {
    if (GROUPS[name]) name = GROUPS[name][0];
    currentView = name;
    $$(".view").forEach((v) => v.classList.add("hidden"));
    const el = $(`#view-${name}`);
    if (el) el.classList.remove("hidden");
    const g = groupOf(name);
    $$("#main-nav .sidebar-link").forEach((b) => {
      const on = b.dataset.group === g;
      b.classList.toggle("active", on);
      if (on) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
    markTabs();
    setDrawer(false);
    window.scrollTo(0, 0);
    refreshView(name);
  }

  async function refreshView(name) {
    try {
      if (name === "home") await loadHome();
      else if (name === "catalog") await loadCatalog();
      else if (name === "zones") await loadZones();
      else if (name === "count") await loadCount();
      else if (name === "variance") await loadVariance();
      else if (name === "receive") await loadReceive();
      else if (name === "setup") { await loadSetup(); }
      else if (name === "menu") await loadMenu();
      else if (name === "sales") await loadSales();
      else if (name === "stops") await loadStops();
      else if (name === "reports") await loadSalesVariance();
      else if (name === "reorder") await loadReorder();
      if (extraViews[name]) await extraViews[name]();
    } catch (e) {
      console.error(e);
    }
  }

  /* ----- Locale ----- */
  async function loadLocale(lang) {
    const data = await api(`/api/locales/${lang}`);
    strings = data.strings || {};
    locale = data.locale || lang;
    applyI18n();
    $$(".locale-switch button").forEach((b) => {
      b.classList.toggle("active", b.dataset.locale === locale);
    });
  }

  async function setLocale(lang) {
    try { localStorage.setItem("osft_locale", lang); } catch (_) { /* private mode */ }
    await loadLocale(lang);
    try {
      // crew logins keep their language on this device only (no 403 from the settings write)
      if (window.OSFT_V1 && !window.OSFT_V1.can("settings")) throw new Error("local only");
      await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ locale: lang }),
      });
    } catch (_) {
      /* settings may fail if truck name empty — locale UI still works */
    }
    await refreshView(currentView);
  }

  /* ----- Home / dashboard ----- */
  async function loadHome() {
    const dash = await api("/api/dashboard");
    settings = dash.settings || {};
    $("#truck-label").textContent = settings.truck_name || "OSFT";
    $("#version-label").textContent = "OSFT v" + (dash.version || "");
    const lc = dash.last_count && (dash.last_count.completed_at || "");
    $("#sidebar-cycle").textContent = lc ? `${t("last_count")}: ${fmtWhen(lc)}` : t("no_count_yet");
    $("#dash-badge").textContent = settings.truck_name || "OSFT";

    const m = (n, l, cls, go) => `<button type="button" class="metric ${cls}" data-goto="${go}"><span class="metric-n">${n}</span><span class="metric-l">${esc(l)}</span></button>`;
    $("#home-stats").innerHTML =
      m(dash.item_count, t("m_items"), "metric--teal", "catalog") +
      m(dash.low_par_count, t("low_par_alert"), dash.low_par_count ? "metric--hot" : "metric--teal", "reorder") +
      m(money(dash.inventory_value || 0), t("m_value"), "metric--pop metric--wide", "zones") +
      m(dash.receive_count, t("m_receives"), "metric--orange", "receive") +
      m(dash.menu_count || 0, t("m_menu"), "metric--orange", "menu") +
      m(dash.sales_import_count || 0, t("m_sales"), "metric--teal", "sales") +
      m(dash.stop_count || 0, t("m_stops"), "metric--pop", "stops");

    const alerts = $("#home-alerts");
    alerts.innerHTML = "";
    if (dash.empty) alerts.innerHTML = `<div class="alert alert-info">${t("empty_inventory")}</div>`;
    if (!settings.setup_complete) alerts.innerHTML += `<div class="alert alert-warn">${t("setup_incomplete")}</div>`;

    const low = $("#home-low-par");
    if (dash.low_par && dash.low_par.length) {
      low.innerHTML = `<div class="panel-head-row"><h2>${t("low_par_alert")}</h2><span class="caption caption--hot">${t("cap_heads_up")}</span></div>
        <div class="table-wrap"><table>
          <thead><tr><th>${t("label_item")}</th><th>${t("label_zone")}</th><th>${t("label_on_hand")}</th><th>PAR</th><th>${t("short")}</th></tr></thead>
          <tbody>${dash.low_par.map((r) => `<tr>
                <td>${esc(r.name)} <span class="badge badge-low">${t("low")}</span></td>
                <td>${zoneBadge(r.zone)}</td>
                <td>${fmtNum(r.on_hand)} ${esc(r.unit)}</td>
                <td>${fmtNum(r.par)}</td>
                <td class="neg">${fmtNum(r.shortfall)}</td></tr>`).join("")}</tbody>
        </table></div>`;
    } else if (!dash.empty) {
      low.innerHTML = `<div class="empty-state"><img src="/static/img/seal.webp" alt="" width="110" height="111" /><p>${t("all_at_par")}</p></div>`;
    } else {
      low.innerHTML = `<div class="empty-state"><img src="/static/img/truck-small.webp" alt="" width="180" height="109" /><p>${t("empty_inventory")}</p></div>`;
    }
  }

  /* ----- Order list (OSBW Order Generator) ----- */
  async function loadReorder() {
    const r = await api("/api/reorder");
    const el = $("#reorder-list");
    if (!r.groups.length) {
      el.innerHTML = `<div class="empty-state"><img src="/static/img/seal.webp" alt="" width="110" height="111" /><p>${t("all_at_par")}</p></div>`;
      return;
    }
    el.innerHTML = r.groups.map((g) => `<div class="vendor-block">
        <h3><span class="caption">${esc(g.vendor || t("no_vendor"))}</span> <span class="muted">${money(g.subtotal)}</span></h3>
        <div class="table-wrap"><table><thead><tr><th>${t("label_item")}</th><th>${t("label_on_hand")}</th><th>PAR</th><th>${t("order_qty")}</th><th>$</th></tr></thead><tbody>
        ${g.lines.map((l) => `<tr><td>${esc(l.name)} ${zoneBadge(l.zone)}</td><td>${fmtNum(l.on_hand)} ${esc(l.unit)}</td><td>${fmtNum(l.par)}</td><td><b>${fmtNum(l.order_qty)}</b> ${esc(l.unit)}</td><td>${l.ext_cost === null ? "—" : money(l.ext_cost)}</td></tr>`).join("")}
        </tbody></table></div></div>`).join("") +
      `<p class="order-total">${t("order_total")}: <b>${money(r.total)}</b> · ${r.line_count} ${t("lines")}</p>`;
  }

  /* ----- Catalog ----- */
  async function loadCatalog() {
    await syncZones();
    try {
      const vs = (await api("/api/vendors")).vendors || [];
      $("#item-vendor").innerHTML = `<option value="">—</option>` + vs.map((v) => `<option value="${v.id}">${esc(v.name)}</option>`).join("");
    } catch (_) { /* vendors need orders permission */ }
    const data = await api("/api/items");
    items = data.items || [];
    const wrap = $("#catalog-list");
    if (!items.length) {
      wrap.innerHTML = `<div class="empty-state"><div class="icon">📦</div><p>${t("empty_inventory")}</p></div>`;
      return;
    }
    wrap.innerHTML = `<table>
      <thead><tr>
        <th>${t("label_name")}</th><th>${t("label_zone")}</th>
        <th>${t("label_on_hand")}</th><th>${t("label_par")}</th>
        <th>${t("label_category")}</th><th></th>
      </tr></thead>
      <tbody>
        ${items
          .map((it) => {
            const low = Number(it.on_hand) < Number(it.par);
            return `<tr>
              <td>${esc(it.name)}${low ? ` <span class="badge badge-low">${t("low")}</span>` : ""}${it.cost == null ? ` <span class="badge badge-example">${t("no_cost")}</span>` : ""}${it.name_es ? `<div class="muted">${esc(it.name_es)}</div>` : ""}</td>
              <td>${zoneBadge(it.zone)}</td>
              <td>${fmtNum(it.on_hand)} ${esc(it.unit)}</td>
              <td>${fmtNum(it.par)}</td>
              <td>${esc(it.category)}</td>
              <td class="row">
                <button type="button" class="btn btn-sm btn-ghost" data-edit="${it.id}">${t("btn_edit")}</button>
                <button type="button" class="btn btn-sm btn-danger" data-del="${it.id}">${t("btn_delete")}</button>
              </td>
            </tr>`;
          })
          .join("")}
      </tbody>
    </table>`;

    wrap.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => openEdit(btn.dataset.edit));
    });
    wrap.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", () => archiveItem(btn.dataset.del));
    });
  }

  function openAdd() {
    $("#item-form").reset();
    $("#item-id").value = "";
    $("#item-onhand").value = "0";
    $("#catalog-form-wrap").classList.remove("hidden");
    hideErr($("#catalog-error"));
    $("#item-name").focus();
  }

  function openEdit(id) {
    const it = items.find((x) => x.id === id);
    if (!it) return;
    $("#item-id").value = it.id;
    $("#item-name").value = it.name;
    $("#item-unit").value = it.unit;
    $("#item-par").value = it.par;
    $("#item-category").value = it.category;
    $("#item-zone").value = it.zone;
    $("#item-onhand").value = it.on_hand;
    $("#item-cost").value = it.cost ?? "";
    ["case_size", "pack", "name_es", "sku", "barcode", "notes"].forEach((k) => { const el = $("#item-" + k.replace("_", "-")); if (el) el.value = it[k] ?? ""; });
    if ($("#item-aliases")) $("#item-aliases").value = (it.aliases || []).join(", ");
    if ($("#item-vendor")) $("#item-vendor").value = it.vendor_id || "";
    $("#catalog-form-wrap").classList.remove("hidden");
    hideErr($("#catalog-error"));
  }

  async function archiveItem(id) {
    if (!confirm(t("confirm_archive"))) return;
    try {
      await api(`/api/items/${id}`, { method: "DELETE" });
      await loadCatalog();
      hideErr($("#catalog-error"));
    } catch (e) {
      showErr($("#catalog-error"), e.message);
    }
  }

  async function saveItem(ev) {
    ev.preventDefault();
    hideErr($("#catalog-error"));
    const id = $("#item-id").value;
    const payload = {
      name: $("#item-name").value,
      unit: $("#item-unit").value,
      par: $("#item-par").value,
      category: $("#item-category").value,
      zone: $("#item-zone").value,
      on_hand: $("#item-onhand").value,
      cost: $("#item-cost").value,
      case_size: $("#item-case-size").value, pack: $("#item-pack").value, name_es: $("#item-name-es").value,
      sku: $("#item-sku").value, barcode: $("#item-barcode").value, notes: $("#item-notes").value,
      vendor_id: $("#item-vendor").value || null,
      aliases: $("#item-aliases").value.split(",").map((x) => x.trim()).filter(Boolean),
    };
    try {
      if (id) {
        await api(`/api/items/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api("/api/items", { method: "POST", body: JSON.stringify(payload) });
      }
      $("#catalog-form-wrap").classList.add("hidden");
      await loadCatalog();
    } catch (e) {
      showErr($("#catalog-error"), e.message);
    }
  }

  /* ----- Zones ----- */
  async function loadZones() {
    const data = await api("/api/zones");
    if (Array.isArray(data.zones)) ZONES = data.zones;
    const map = $("#zones-map");
    map.innerHTML = ZONES.map((z) => {
      const list = (data.by_zone && data.by_zone[z]) || [];
      const lis =
        list.length === 0
          ? `<li class="muted">—</li>`
          : list
              .map(
                (i) =>
                  `<li>${esc(i.name)} <span class="muted">(${fmtNum(i.on_hand)} ${esc(i.unit)})</span></li>`
              )
              .join("");
      return `<div class="zone-card">
        <h3>${zoneBadge(z)}</h3>
        <ul>${lis}</ul>
      </div>`;
    }).join("");
  }

  async function syncZones() {
    try {
      const r = await api("/api/sections");
      ZONES = r.sections.map((x) => x.key);
      SECNAMES = Object.fromEntries(r.sections.map((x) => [x.key, x.name]));
    } catch (_) { /* keep defaults */ }
    const sel = $("#item-zone");
    if (sel) { const v = sel.value; sel.innerHTML = ZONES.map((z) => `<option value="${esc(z)}">${esc(zoneName(z))}</option>`).join(""); if (v) sel.value = v; }
  }

  /* ----- Count walk ----- */
  async function loadCount() {
    await syncZones();
    const latest = await api("/api/counts/latest");
    const itemsData = await api("/api/items");
    items = itemsData.items || [];

    const status = $("#count-status");
    const form = $("#count-form");
    const completeBtn = $("#btn-complete-count");

    // Check for in-progress
    const all = await api("/api/counts");
    const inProg = (all.sessions || []).find((s) => s.status === "in_progress");

    const V13 = window.OSFT_V13;
    if (V13) await V13.countChrome(inProg);
    if (inProg) {
      activeCountId = inProg.id;
      status.textContent = `${t("count_in_progress")} ${fmtWhen(inProg.started_at)}`;
      completeBtn.disabled = false;
      renderCountForm(V13 ? V13.scopeItems(items, inProg) : items, inProg.counts || {});
    } else {
      activeCountId = null;
      completeBtn.disabled = true;
      if (latest.session) {
        const ls = latest.session;
        status.textContent = `${t("last_count")}: ${ls.business_date || fmtWhen(ls.completed_at)}${ls.type_name ? " · " + ls.type_name : ""}${ls.counted_by ? " · " + ls.counted_by : ""} (${Object.keys(ls.counts || {}).length} ${t("m_items").toLowerCase()})`;
        renderCountForm(items, latest.session.counts || {}, true);
      } else {
        status.textContent = t("no_counts_start");
        form.innerHTML = items.length
          ? `<p class="muted">${t("press_start")} “${t("btn_start_count")}”.</p>`
          : `<div class="empty-state"><p>${t("empty_inventory")}</p></div>`;
      }
    }
  }

  function renderCountForm(itemList, counts, readonly) {
    const form = $("#count-form");
    if (!itemList.length) {
      form.innerHTML = `<div class="empty-state"><p>${t("empty_inventory")}</p></div>`;
      return;
    }
    const byZone = {};
    ZONES.forEach((z) => (byZone[z] = []));
    itemList.forEach((i) => {
      (byZone[i.zone] || (byZone[i.zone] = [])).push(i);
    });

    form.innerHTML = ZONES.map((z) => {
      const list = byZone[z] || [];
      if (!list.length) return "";
      const rows = list
        .map((i) => {
          const val = counts[i.id] !== undefined ? counts[i.id] : i.on_hand;
          return `<tr>
            <td>${esc(i.name)}</td>
            <td class="muted">${esc(i.unit)}</td>
            <td>
              <div class="stepper">
                <button type="button" class="step-btn" data-step="-1" aria-label="${esc(t("minus_one"))} ${esc(i.name)}" ${readonly ? "disabled" : ""}>−</button>
                <input type="number" min="0" step="any" inputmode="decimal" data-count-item="${i.id}" aria-label="${esc(i.name)} (${esc(i.unit)})"
                  value="${val}" ${readonly ? "readonly disabled" : ""} />
                <button type="button" class="step-btn" data-step="1" aria-label="${esc(t("plus_one"))} ${esc(i.name)}" ${readonly ? "disabled" : ""}>+</button>
              </div>
            </td>
          </tr>`;
        })
        .join("");
      return `<div class="zone-card" style="margin-bottom:.75rem">
        <h3>${zoneBadge(z)}</h3>
        <div class="table-wrap"><table>
          <thead><tr><th>${t("label_item")}</th><th>${t("label_unit")}</th><th>${t("qty")}</th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>
      </div>`;
    }).join("");

    if (!readonly) {
      form.querySelectorAll(".step-btn").forEach((b) => b.addEventListener("click", () => {
        const inp = b.parentElement.querySelector("input");
        const v = Math.max(0, (parseFloat(inp.value) || 0) + Number(b.dataset.step));
        inp.value = Number.isInteger(v) ? v : v.toFixed(2);
        inp.dispatchEvent(new Event("change"));
      }));
      form.querySelectorAll("[data-count-item]").forEach((inp) => {
        inp.addEventListener("change", debounce(saveCountProgress, 400));
      });
    }
  }

  function debounce(fn, ms) {
    let tmr;
    return function (...args) {
      clearTimeout(tmr);
      tmr = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  async function gatherCounts() {
    const counts = {};
    $$("[data-count-item]").forEach((inp) => {
      counts[inp.dataset.countItem] = inp.value;
    });
    return counts;
  }

  async function saveCountProgress() {
    if (!activeCountId) return;
    hideErr($("#count-error"));
    try {
      const counts = await gatherCounts();
      const extra = window.OSFT_V13 ? window.OSFT_V13.checklistBody() : {};
      await api(`/api/counts/${activeCountId}`, {
        method: "PUT",
        body: JSON.stringify({ counts, ...extra }),
      });
    } catch (e) {
      showErr($("#count-error"), e.message);
    }
  }

  async function startCount() {
    hideErr($("#count-error"));
    try {
      const body = window.OSFT_V13 ? window.OSFT_V13.startBody() : {};
      const data = await api("/api/counts/start", { method: "POST", body: JSON.stringify(body) });
      activeCountId = data.session.id;
      await loadCount();
    } catch (e) {
      showErr($("#count-error"), e.message);
    }
  }

  async function completeCount() {
    if (!activeCountId) return;
    hideErr($("#count-error"));
    try {
      await saveCountProgress();
      const done = await api(`/api/counts/${activeCountId}/complete`, { method: "POST", body: "{}" });
      if (window.OSFT_V13) window.OSFT_V13.lastSummary = done.session;
      activeCountId = null;
      await loadCount();
      // crew logins without "reports" stay on the count screen (summary shown there) instead of hitting a 403
      if (!window.OSFT_V1 || window.OSFT_V1.can("reports")) showView("variance");
    } catch (e) {
      showErr($("#count-error"), e.message);
    }
  }

  /* ----- Variance ----- */
  async function loadVariance() {
    const data = await api("/api/variance");
    const meta = $("#variance-meta");
    const table = $("#variance-table");
    if (!data.session) {
      meta.textContent = t("no_count_yet");
      table.innerHTML = "";
      return;
    }
    const ss = data.session;
    meta.textContent = `${t("last_count")}: ${fmtWhen(ss.completed_at)}` + (ss.type_name ? ` · ${ss.type_name}${ss.scope && ss.scope.full === false ? " — " + t("ct_partial_short") : ""}${ss.counted_by ? " · " + ss.counted_by : ""}` : "");
    const rows = data.variance || [];
    if (!rows.length) {
      table.innerHTML = `<p class="muted">${t("no_counted_items")}</p>`;
      return;
    }
    table.innerHTML = `<table>
      <thead><tr>
        <th>${t("label_item")}</th><th>${t("label_zone")}</th><th>${t("counted")}</th><th>PAR</th>
        <th>${t("vs_par")}</th><th>${t("prior")}</th><th>${t("vs_prior")}</th>
      </tr></thead>
      <tbody>
        ${rows
          .map((r) => {
            const vp = r.vs_par;
            const vpr = r.vs_prior;
            return `<tr>
              <td>${esc(r.name)}${r.below_par ? ` <span class="badge badge-low">${t("low")}</span>` : ""}</td>
              <td>${zoneBadge(r.zone)}</td>
              <td>${fmtNum(r.counted)} ${esc(r.unit)}</td>
              <td>${fmtNum(r.par)}</td>
              <td class="${vp < 0 ? "neg" : "pos"}">${fmtNum(vp)}</td>
              <td>${r.prior === null ? "—" : fmtNum(r.prior)}</td>
              <td class="${vpr === null ? "" : vpr < 0 ? "neg" : "pos"}">${vpr === null ? "—" : fmtNum(vpr)}</td>
            </tr>`;
          })
          .join("")}
      </tbody>
    </table>`;
  }

  /* ----- Receive ----- */
  async function loadReceive() {
    const itemsData = await api("/api/items");
    items = itemsData.items || [];
    const sel = $("#recv-item");
    sel.innerHTML = items.length
      ? items.map((i) => `<option value="${i.id}">${esc(i.name)} (${esc(i.unit)})</option>`).join("")
      : `<option value="">—</option>`;

    const rec = await api("/api/receives");
    const list = $("#receive-list");
    const rows = rec.receives || [];
    if (!rows.length) {
      list.innerHTML = `<p class="muted">${t("no_receives")}</p>`;
      return;
    }
    list.innerHTML = `<table>
      <thead><tr><th>${t("label_date")}</th><th>${t("label_item")}</th><th>${t("qty")}</th><th>${t("note")}</th><th>${t("photos")}</th></tr></thead>
      <tbody>
        ${rows
          .slice(0, 20)
          .map(
            (r) => `<tr>
            <td class="muted">${esc(fmtWhen(r.received_at))}</td>
            <td>${esc(r.item_name)}</td>
            <td>+${fmtNum(r.qty)} ${esc(r.unit)}</td>
            <td>${esc([r.vendor, r.note].filter(Boolean).join(" · "))}${r.unit_cost != null ? ` <span class="muted">@ ${money(r.unit_cost)}</span>` : ""}${exBadge(r)}</td>
            <td>${(r.photos || []).map((p) => `<a href="/photos/${encodeURIComponent(p)}" target="_blank"><img class="thumb" src="/photos/${encodeURIComponent(p)}" alt="photo" onerror="this.replaceWith(document.createTextNode('📄'))"/></a>
              <button type="button" class="btn btn-sm btn-ghost" data-airead="${r.id}|${esc(p)}" title="AI">🤖</button>`).join("")}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
    list.querySelectorAll("[data-airead]").forEach((b) => b.addEventListener("click", () => {
      const [rid, name] = b.dataset.airead.split("|");
      readPhotoAI(rid, name);
    }));
  }

  async function saveReceive(ev) {
    ev.preventDefault();
    hideErr($("#receive-error"));
    try {
      await api("/api/receives", {
        method: "POST",
        body: JSON.stringify({
          item_id: $("#recv-item").value,
          qty: $("#recv-qty").value,
          note: $("#recv-note").value,
          vendor: $("#recv-vendor").value,
          unit_cost: $("#recv-cost").value,
        }),
      }).then(async (r) => {
        const f = $("#recv-photo").files[0];
        if (f) {
          const fd = new FormData();
          fd.append("photo", f);
          await apiForm(`/api/receives/${r.receive.id}/photos`, fd);
        }
        return r;
      });
      $("#recv-qty").value = "";
      $("#recv-note").value = "";
      $("#recv-cost").value = "";
      $("#recv-photo").value = "";
      await loadReceive();
    } catch (e) {
      showErr($("#receive-error"), e.message);
    }
  }

  /* ----- Setup ----- */
  async function loadSetup() {
    const data = await api("/api/settings");
    settings = data.settings || {};
    $("#setup-truck").value = settings.truck_name || "";
    $("#setup-units").value = settings.units || "imperial";
    $("#setup-locale").value = settings.locale || "en";
    hideErr($("#setup-error"));
    $("#setup-ok").classList.add("hidden");
  }

  async function saveSetup(ev) {
    ev.preventDefault();
    hideErr($("#setup-error"));
    $("#setup-ok").classList.add("hidden");
    try {
      const data = await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({
          truck_name: $("#setup-truck").value,
          units: $("#setup-units").value,
          locale: $("#setup-locale").value,
        }),
      });
      settings = data.settings;
      $("#truck-label").textContent = settings.truck_name || "OSFT";
      if (settings.locale !== locale) {
        await loadLocale(settings.locale);
      }
      $("#setup-ok").classList.remove("hidden");
    } catch (e) {
      showErr($("#setup-error"), e.message);
    }
  }

  /* ----- Seed ----- */
  async function seedDemo() {
    if (!confirm(t("confirm_seed"))) return;
    await api("/api/seed", { method: "POST", body: "{}" });
    await loadHome();
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* =====================================================================
     v0.2 — Menu/recipes, Sales import + variance, Stops/load list,
     receive photos, AI reader settings
     ===================================================================== */
  async function apiForm(path, formData) {
    const res = await fetch(path, { method: "POST", body: formData, headers: { Accept: "application/json" } });
    let body = null;
    try { body = await res.json(); } catch (_) { body = { ok: false, error: `HTTP ${res.status}` }; }
    if (!res.ok) throw new Error((body && body.error) || `HTTP ${res.status}`);
    return body;
  }
  const money = (n) => (n === null || n === undefined ? "—" : (Number(n) < 0 ? "-$" : "$") + Math.abs(Number(n)).toFixed(2));
  const fmtWhen = (iso) => { const d = new Date(iso); return isNaN(d) ? String(iso || "") : d.toLocaleString(locale, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); };
  const exBadge = (o) => (o && o.example ? ` <span class="badge badge-example">${t("example")}</span>` : "");
  function todayISO(offsetDays = 0) {
    const d = new Date(Date.now() + offsetDays * 864e5);
    return new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
  }

  /* ----- Menu ----- */
  let menu = [];
  async function loadMenu() {
    items = (await api("/api/items")).items || [];
    menu = (await api("/api/menu")).menu || [];
    const wrap = $("#menu-list");
    if (!menu.length) { wrap.innerHTML = `<p class="muted">${t("menu_empty")}</p>`; return; }
    wrap.innerHTML = `<table><thead><tr>
      <th>${t("label_name")}</th><th>${t("label_menu_price")}</th><th>${t("plate_cost")}</th>
      <th>${t("food_cost_pct")}</th><th>${t("margin")}</th><th></th></tr></thead><tbody>
      ${menu.map((m) => `<tr>
        <td>${esc(m.name)}${exBadge(m)}<div class="muted">${m.ingredient_lines.map((l) => `${fmtNum(l.qty)} ${esc(l.unit)} ${esc(l.name)}`).join(" · ")}</div>
          ${m.missing_costs.length ? `<div class="muted neg">${t("missing_cost")}: ${esc(m.missing_costs.join(", "))}</div>` : ""}</td>
        <td>${money(m.price)}</td><td>${money(m.plate_cost)}</td>
        <td class="${m.food_cost_pct > 35 ? "neg" : "pos"}">${m.food_cost_pct === null ? "—" : m.food_cost_pct + "%"}</td>
        <td>${money(m.margin)}${m.margin_pct === null ? "" : ` <span class="muted">(${m.margin_pct}%)</span>`}</td>
        <td class="row"><button type="button" class="btn btn-sm btn-ghost" data-medit="${m.id}">${t("btn_edit")}</button>
          <button type="button" class="btn btn-sm btn-danger" data-mdel="${m.id}">${t("btn_delete")}</button></td>
      </tr>`).join("")}</tbody></table>`;
    wrap.querySelectorAll("[data-medit]").forEach((b) => b.addEventListener("click", () => openMenuForm(b.dataset.medit)));
    wrap.querySelectorAll("[data-mdel]").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm(t("confirm_archive"))) return;
      await api(`/api/menu/${b.dataset.mdel}`, { method: "DELETE" });
      await loadMenu();
    }));
  }
  function ingRow(ing = {}) {
    const div = document.createElement("div");
    div.className = "row ing-row";
    div.innerHTML = `<select class="ing-item">${items.map((i) => `<option value="${i.id}" ${i.id === ing.item_id ? "selected" : ""}>${esc(i.name)} (${esc(i.unit)})</option>`).join("")}</select>
      <input class="ing-qty" type="number" min="0" step="any" inputmode="decimal" value="${ing.qty ?? ""}" placeholder="${t("qty")}" />
      <button type="button" class="btn btn-sm btn-ghost ing-del">✕</button>`;
    div.querySelector(".ing-del").addEventListener("click", () => div.remove());
    $("#menu-ings").appendChild(div);
  }
  function openMenuForm(id) {
    const m = menu.find((x) => x.id === id) || { ingredients: [] };
    $("#menu-id").value = m.id || "";
    $("#menu-name").value = m.name || "";
    $("#menu-price").value = m.price ?? "";
    $("#menu-category").value = m.category || "";
    $("#menu-posnames").value = (m.pos_names || []).join(", ");
    $("#menu-ings").innerHTML = "";
    (m.ingredients.length ? m.ingredients : [{}]).forEach(ingRow);
    $("#menu-form-wrap").classList.remove("hidden");
    hideErr($("#menu-error"));
  }
  async function saveMenu(ev) {
    ev.preventDefault();
    hideErr($("#menu-error"));
    const payload = {
      name: $("#menu-name").value, price: $("#menu-price").value, category: $("#menu-category").value,
      pos_names: $("#menu-posnames").value.split(",").map((s) => s.trim()).filter(Boolean),
      ingredients: $$("#menu-ings .ing-row").map((r) => ({ item_id: $(".ing-item", r).value, qty: $(".ing-qty", r).value }))
        .filter((x) => x.item_id && x.qty !== ""),
    };
    const id = $("#menu-id").value;
    try {
      await api(id ? `/api/menu/${id}` : "/api/menu", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
      $("#menu-form-wrap").classList.add("hidden");
      await loadMenu();
    } catch (e) { showErr($("#menu-error"), e.message); }
  }

  /* ----- Sales import ----- */
  let adapters = [];
  let lastPreview = null;
  async function loadSales() {
    if (!adapters.length) {
      adapters = (await api("/api/pos/adapters")).adapters || [];
      $("#sales-adapter").innerHTML = `<option value="">${t("auto_detect")}</option>` + adapters.map((a) =>
        `<option value="${a.key}" ${a.available ? "" : "disabled"}>${esc(a.label)}${a.verified ? "" : " ⚠"}</option>`).join("");
    }
    if (!$("#sales-date").value) $("#sales-date").value = todayISO();
    const list = (await api("/api/sales")).imports || [];
    $("#sales-list").innerHTML = list.length ? `<table><thead><tr><th>${t("label_date")}</th><th>${t("label_csv")}</th><th>POS</th><th>${t("qty")}</th><th>$</th><th></th></tr></thead><tbody>
      ${list.map((i) => `<tr><td class="muted">${esc(fmtWhen(i.imported_at))}</td><td>${esc(i.filename)}${exBadge(i)}</td><td>${esc(i.adapter)}</td>
        <td>${fmtNum(i.total_qty)}</td><td>${money(i.total_sales)}</td>
        <td><button type="button" class="btn btn-sm btn-danger" data-sdel="${i.id}">✕</button></td></tr>`).join("")}</tbody></table>`
      : `<p class="muted">${t("sales_none")}</p>`;
    $$("#sales-list [data-sdel]").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm(t("confirm_delete"))) return;
      await api(`/api/sales/${b.dataset.sdel}`, { method: "DELETE" });
      await loadSales();
    }));
    await loadSalesVariance();
  }
  function salesForm(includeMapping) {
    const fd = new FormData();
    const f = $("#sales-file").files[0];
    if (f) fd.append("file", f);
    const ad = $("#sales-adapter").value || (lastPreview && lastPreview.adapter) || "";
    if (ad) fd.append("adapter", ad);
    fd.append("default_date", $("#sales-date").value || "");
    if (includeMapping) {
      const m = {};
      $$("#sales-mapping select").forEach((s) => { if (s.value) m[s.dataset.field] = s.value; });
      fd.append("mapping", JSON.stringify(m));
    }
    return fd;
  }
  async function previewSales(useMapping) {
    hideErr($("#sales-error"));
    try {
      const p = await apiForm("/api/pos/preview", salesForm(useMapping === true));
      lastPreview = p;
      const a = p.adapter_info;
      $("#sales-adapter-note").innerHTML = `<b>${esc(a.label)}</b> — ${esc(a.notes || "")} ${a.verified ? "" : `<span class="neg">${t("unverified")}</span>`}`;
      const mapEl = $("#sales-mapping");
      mapEl.classList.remove("hidden");
      mapEl.innerHTML = p.fields.map((f) => `<div><label>${esc(t("field_" + f))}</label>
        <select data-field="${f}"><option value="">—</option>${p.headers.map((h) => `<option ${p.mapping[f] === h ? "selected" : ""}>${esc(h)}</option>`).join("")}</select></div>`).join("");
      mapEl.querySelectorAll("select").forEach((s) => s.addEventListener("change", () => previewSales(true)));
      if (p.parse_error) showErr($("#sales-error"), p.parse_error);
      $("#btn-sales-import").disabled = !p.line_count;
      $("#sales-preview").innerHTML = `<p class="muted">${p.line_count} ${t("lines_found")} · ${p.row_count} rows</p>
        ${p.unmatched.length ? `<div class="alert alert-warn">${t("unmatched")}: ${esc(p.unmatched.join(", "))}</div>` : ""}
        <table><thead><tr><th>${t("label_date")}</th><th>${t("field_menu_item")}</th><th>${t("qty")}</th><th>$</th></tr></thead><tbody>
        ${p.lines.map((l) => `<tr><td>${esc(l.date || "—")}</td><td>${esc(l.menu_item)}${l.menu_item_id ? " ✓" : ""}</td><td>${fmtNum(l.qty)}</td><td>${money(l.price)}</td></tr>`).join("")}</tbody></table>`;
    } catch (e) { showErr($("#sales-error"), e.message); }
  }
  async function importSales(ev) {
    ev.preventDefault();
    hideErr($("#sales-error"));
    try {
      await apiForm("/api/pos/import", salesForm(true));
      $("#sales-preview").innerHTML = `<div class="alert alert-ok">${t("saved")}</div>`;
      $("#sales-mapping").classList.add("hidden");
      $("#btn-sales-import").disabled = true;
      $("#sales-file").value = "";
      lastPreview = null;
      await loadSales();
    } catch (e) { showErr($("#sales-error"), e.message); }
  }
  async function loadSalesVariance() {
    const v = await api("/api/variance/sales");
    const el = $("#sales-var");
    if (!v.ready) { el.innerHTML = `<p class="muted">${esc(v.reason)}</p>`; return; }
    const um = Object.entries(v.unmatched_sales || {});
    el.innerHTML = `<p class="muted">${esc(v.period[0])} → ${esc(v.period[1])} · ${t("total_var_cost")}: <b class="${v.total_variance_cost > 0 ? "neg" : "pos"}">${money(v.total_variance_cost)}</b>${v.start && v.start.type_name ? ` · ${esc(v.start.type_name)} → ${esc(v.end.type_name)}` : ""}</p>
      ${(v.skipped_partials || []).length ? `<p class="muted sv-skipped">${t("sv_skipped_partials").replace("{n}", v.skipped_partials.length)}</p>` : ""}
      ${um.length ? `<div class="alert alert-warn">${t("unmatched")}: ${esc(um.map(([n, q]) => `${n} ×${fmtNum(q)}`).join(", "))}</div>` : ""}
      <table><thead><tr><th>${t("label_item")}</th><th>${t("counted_usage")}</th><th>${t("theoretical")}</th><th>${t("variance")}</th><th>$</th></tr></thead><tbody>
      ${v.rows.map((r) => `<tr><td>${esc(r.name)}</td><td>${fmtNum(r.counted_usage)} ${esc(r.unit)}</td><td>${fmtNum(r.theoretical)}</td>
        <td class="${(r.variance || 0) > 0.001 ? "neg" : "pos"}">${r.variance === null ? esc(r.note || "—") : fmtNum(r.variance)}${r.variance_pct === null || r.variance_pct === undefined ? "" : ` <span class="muted">(${r.variance_pct}%)</span>`}</td>
        <td>${money(r.variance_cost)}</td></tr>`).join("")}</tbody></table>
      <p class="muted">${t("var_explain")}</p>`;
  }

  /* ----- Stops / load list ----- */
  let stops = [];
  async function loadStops() {
    items = (await api("/api/items")).items || [];
    stops = (await api("/api/stops")).stops || [];
    const sel = $("#load-stop");
    const prev = sel.value;
    sel.innerHTML = stops.length ? stops.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join("") : `<option value="">—</option>`;
    if (prev && stops.some((s) => s.id === prev)) sel.value = prev;
    if (!$("#load-date").value) $("#load-date").value = todayISO(1);
    await renderLoadList();
  }
  async function renderLoadList() {
    const sid = $("#load-stop").value;
    const el = $("#load-list");
    if (!sid) { el.innerHTML = `<p class="muted">${t("stops_empty")}</p>`; return; }
    $("#btn-print-load").href = `/print/loadlist/${sid}?date=${encodeURIComponent($("#load-date").value)}`;
    const d = await api(`/api/stops/${sid}/loadlist`);
    el.innerHTML = `${d.stop.notes ? `<p class="muted">${esc(d.stop.notes)}</p>` : ""}
      ${d.short_count ? `<div class="alert alert-warn">${d.short_count} ${t("short_items")}</div>` : ""}
      <table><thead><tr><th>${t("label_item")}</th><th>${t("label_zone")}</th><th>${t("load")}</th><th>${t("label_on_hand")}</th><th>${t("buy_prep")}</th></tr></thead><tbody>
      ${d.rows.map((r) => `<tr><td>${esc(r.name)}${r.par_source === "item" ? ' <span class="muted">*</span>' : ""}</td><td>${zoneBadge(r.zone)}</td>
        <td>${fmtNum(r.load)} ${esc(r.unit)}</td><td>${fmtNum(r.on_hand)}</td><td class="${r.short > 0 ? "neg" : ""}">${r.short > 0 ? fmtNum(r.short) : ""}</td></tr>`).join("")}
      </tbody></table><p class="muted">* ${t("par_from_item")}</p>`;
  }
  function openStopForm(id) {
    const s = stops.find((x) => x.id === id) || { pars: {} };
    $("#stop-id").value = s.id || "";
    $("#stop-name").value = s.name || "";
    $("#stop-notes").value = s.notes || "";
    $("#stop-pars").innerHTML = `<table><thead><tr><th>${t("label_item")}</th><th>${t("label_par")}</th><th>${t("stop_par")}</th></tr></thead><tbody>
      ${items.map((i) => `<tr><td>${esc(i.name)} <span class="muted">${esc(i.unit)}</span></td><td class="muted">${fmtNum(i.par)}</td>
        <td><input type="number" min="0" step="any" inputmode="decimal" data-spar="${i.id}" value="${s.pars[i.id] ?? ""}" /></td></tr>`).join("")}</tbody></table>`;
    $("#stop-form-wrap").classList.remove("hidden");
    hideErr($("#stops-error"));
  }
  async function saveStop(ev) {
    ev.preventDefault();
    hideErr($("#stops-error"));
    const pars = {};
    $$("#stop-pars [data-spar]").forEach((i) => { if (i.value !== "") pars[i.dataset.spar] = i.value; });
    const id = $("#stop-id").value;
    try {
      const r = await api(id ? `/api/stops/${id}` : "/api/stops", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify({ name: $("#stop-name").value, notes: $("#stop-notes").value, pars }),
      });
      $("#stop-form-wrap").classList.add("hidden");
      $("#load-stop").value = r.stop.id;
      await loadStops();
      $("#load-stop").value = r.stop.id;
      await renderLoadList();
    } catch (e) { showErr($("#stops-error"), e.message); }
  }

  /* ----- Receive photos + AI ----- */
  async function readPhotoAI(rid, name) {
    const box = $("#ai-suggest");
    box.classList.remove("hidden");
    box.innerHTML = `<div class="alert alert-info">${t("loading")}</div>`;
    try {
      const r = await api(`/api/receives/${rid}/photos/${encodeURIComponent(name)}/read`, { method: "POST", body: "{}" });
      const s = r.suggestion || {};
      box.innerHTML = `<div class="alert alert-info"><b>${t("ai_suggest")}</b> ${esc(s.vendor || "")} ${esc(s.date || "")}
        <ul>${(s.lines || []).map((l) => `<li>${esc(l.description)} — ${fmtNum(l.qty)} ${esc(l.unit || "")} @ ${money(l.unit_cost)}</li>`).join("")}</ul>
        <span class="muted">${t("ai_confirm")}</span></div>`;
    } catch (e) {
      box.innerHTML = `<div class="alert alert-warn">${esc(e.message)}</div>`;
    }
  }

  /* ----- AI settings ----- */
  async function loadAISettings() {
    const a = (await api("/api/settings/ai")).ai_reader;
    $("#ai-enabled").checked = a.enabled;
    $("#ai-model").value = a.model;
    $("#ai-endpoint").value = a.endpoint;
    $("#ai-key").value = "";
    $("#ai-key").placeholder = a.has_key ? "•••••••• " + t("ai_key_saved") : "";
    hideErr($("#ai-error"));
    $("#ai-ok").classList.add("hidden");
  }
  async function saveAISettings(ev, clear) {
    if (ev) ev.preventDefault();
    hideErr($("#ai-error"));
    const body = clear ? { clear_key: true, enabled: false } : {
      enabled: $("#ai-enabled").checked, model: $("#ai-model").value, endpoint: $("#ai-endpoint").value,
      api_key: $("#ai-key").value || undefined,
    };
    try {
      await api("/api/settings/ai", { method: "PUT", body: JSON.stringify(body) });
      await loadAISettings();
      $("#ai-ok").classList.remove("hidden");
    } catch (e) { showErr($("#ai-error"), e.message); }
  }

  /* ----- Boot ----- */
  async function init() {
    $("#main-nav").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-group]");
      if (btn) showView(btn.dataset.group);
    });
    document.addEventListener("click", (e) => {
      const tab = e.target.closest("[data-tab]");
      if (tab) return showView(tab.dataset.tab);
      const go = e.target.closest("[data-goto]");
      if (go) showView(go.dataset.goto);
    });
    $("#menu-toggle").addEventListener("click", () => setDrawer(!document.body.classList.contains("drawer-open")));
    $("#scrim").addEventListener("click", () => setDrawer(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") setDrawer(false); });
    $("#btn-print-order").addEventListener("click", () => window.print());
    $$(".locale-switch button").forEach((b) => {
      b.addEventListener("click", () => setLocale(b.dataset.locale));
    });
    $("#btn-seed").addEventListener("click", seedDemo);
    $("#btn-add-item").addEventListener("click", openAdd);
    $("#btn-cancel-item").addEventListener("click", () => {
      $("#catalog-form-wrap").classList.add("hidden");
    });
    $("#item-form").addEventListener("submit", saveItem);
    $("#btn-start-count").addEventListener("click", startCount);
    $("#btn-complete-count").addEventListener("click", completeCount);
    $("#receive-form").addEventListener("submit", saveReceive);
    $("#setup-form").addEventListener("submit", saveSetup);
    $("#btn-add-menu").addEventListener("click", () => openMenuForm(null));
    $("#btn-add-ing").addEventListener("click", () => ingRow());
    $("#btn-cancel-menu").addEventListener("click", () => $("#menu-form-wrap").classList.add("hidden"));
    $("#menu-form").addEventListener("submit", saveMenu);
    $("#btn-sales-preview").addEventListener("click", () => previewSales(false));
    $("#sales-file").addEventListener("change", () => { lastPreview = null; previewSales(false); });
    $("#sales-adapter").addEventListener("change", () => { lastPreview = null; if ($("#sales-file").files[0]) previewSales(false); });
    $("#sales-form").addEventListener("submit", importSales);
    $("#btn-add-stop").addEventListener("click", () => openStopForm(null));
    $("#btn-edit-stop").addEventListener("click", () => openStopForm($("#load-stop").value));
    $("#btn-cancel-stop").addEventListener("click", () => $("#stop-form-wrap").classList.add("hidden"));
    $("#stop-form").addEventListener("submit", saveStop);
    $("#load-stop").addEventListener("change", renderLoadList);
    $("#load-date").addEventListener("change", renderLoadList);

    try {
      const ob = await api("/api/onboarding");
      let lang = "en";
      try { const s = await api("/api/settings"); settings = s.settings || {}; lang = settings.locale || "en"; } catch (_) { /* may need login */ }
      const qLang = new URLSearchParams(location.search).get("lang");
      await loadLocale((qLang === "es" || qLang === "en") ? qLang : (localStorage.getItem("osft_locale") || lang));
      $("#truck-label").textContent = (ob.business && ob.business.name) || settings.truck_name || "OSFT";
      if (window.OSFT.boot) await window.OSFT.boot(ob);
      else showView(ob.onboarding.completed ? "home" : "setup");
    } catch (e) {
      console.error("Boot failed", e);
      document.body.insertAdjacentHTML(
        "afterbegin",
        `<div class="alert alert-error" style="margin:1rem">Failed to reach API: ${esc(e.message)}</div>`
      );
    }
  }

  const exported = {
    api, apiForm, t, esc, fmtNum, money, fmtWhen, exBadge, zoneBadge, showErr, hideErr, showView, refreshView, todayISO,
    $, $$, syncZones, zoneName, setDrawer, loadLocale,
    registerView(name, fn) { extraViews[name] = fn; },
    get zones() { return ZONES; }, get locale() { return locale; }, get currentView() { return currentView; },
    get items() { return items; },
  };
  window.OSFT = window.OSFT || {};
  Object.defineProperties(window.OSFT, Object.getOwnPropertyDescriptors(exported));

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
