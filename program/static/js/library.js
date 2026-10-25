/* OSFT — Settings › Library (the full manual) and the Help tutor (bottom-right on every screen).
   The manual comes from /api/library/<lang> (library/<lang>/*.md). Help answers from the manual in the
   browser at no cost; when the owner has connected an AI (Settings › AI) it sends the question, the pages it
   found and a read-only truck summary to /api/library/ask and teaches step by step. Nothing here saves data. */
(function () {
  "use strict";
  const O = () => window.OSFT;
  const t = (k) => O().t(k);
  const tf = (k, o) => Object.entries(o).reduce((s, [a, b]) => s.replace("{" + a + "}", b), t(k));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const lang = () => (O().locale === "es" ? "es" : "en");

  /* ---------- manual ---------- */
  const manuals = {};
  let ai = { on: false, label: "", provider: "" };
  const aiName = () => { const k = "ai_p_" + ai.provider; const v = t(k); return v !== k ? v : (ai.label || "AI"); };
  async function manual(force) {
    const l = lang();
    if (!manuals[l] || force) {
      const r = await O().api("/api/library/" + l);
      manuals[l] = index(r.manual);
      ai = r.ai || ai;
    }
    return manuals[l];
  }

  const inl = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>").replace(/(^|[\s(])\*(\S.*?)\*/g, "$1<i>$2</i>");
  function md(src) {
    const out = []; let list = null;
    for (const raw of String(src || "").split("\n")) {
      const l = raw.trimEnd(); const ul = l.match(/^\s*[-*] (.*)/), ol = l.match(/^\s*\d+[.)] (.*)/);
      if (ul || ol) {
        const tag = ul ? "ul" : "ol";
        if (!list || list !== tag) { if (list) out.push(`</${list}>`); out.push(`<${tag}>`); list = tag; }
        out.push(`<li>${inl((ul || ol)[1])}</li>`); continue;
      }
      if (list) { out.push(`</${list}>`); list = null; }
      const h = l.match(/^#{2,4} (.*)/);
      if (h) out.push(`<p><b>${inl(h[1])}</b></p>`);
      else if (l.trim()) out.push(`<p>${inl(l)}</p>`);
    }
    if (list) out.push(`</${list}>`);
    return out.join("");
  }
  const plain = (s) => String(s || "").replace(/[*`#]/g, "").replace(/\s+/g, " ").trim();

  /* ---------- search (BM25 over topics, English + Spanish) ---------- */
  const STOP = new Set(("a an and are as at be by can do does for from how i if in into is it its me my of on or so that the this to was what when where which who why will with you your " +
    "a al como con cual cuando de del donde el ella en es esta este esto hay la las le lo los me mi mis no o para pero por que se si sin su sus te tu tus un una unos y yo").split(" "));
  const fold = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
  const stem = (w) => (w.length > 4 ? w.replace(/(ings|ing|ies|es|s|ed)$/, (m) => (m === "ies" ? "y" : "")) : w);
  const tok = (s) => (fold(s).match(/[a-z0-9]+/g) || []).filter((w) => !STOP.has(w)).map(stem);
  const SYN = { password: ["pin"], contrasena: ["pin"], login: ["pin", "person"], employee: ["crew", "person"], empleado: ["equipo", "persona"],
    staff: ["crew"], key: ["ai"], clave: ["ia"], chatgpt: ["ai"], claude: ["ai"], grok: ["ai"], square: ["pos"], toast: ["pos"], clover: ["pos"],
    waste: ["variance"], merma: ["variacion"], recipe: ["plate", "ingredient"], receta: ["platillo", "ingrediente"], buy: ["order"], comprar: ["pedido"],
    microphone: ["mic", "voice"], microfono: ["voz"], talk: ["voice"], hablar: ["voz"], delivery: ["receive"], entrega: ["recib"] };
  function index(m) {
    const docs = [];
    m.chapters.forEach((c) => c.topics.forEach((tp) => {
      const words = [...tok(tp.title), ...tok(tp.title), ...tok(c.title), ...tok(tp.body)];
      const f = {}; words.forEach((w) => (f[w] = (f[w] || 0) + 1));
      docs.push({ c, t: tp, f, n: words.length });
    }));
    const df = {}; docs.forEach((d) => Object.keys(d.f).forEach((w) => (df[w] = (df[w] || 0) + 1)));
    m._docs = docs; m._df = df; m._avg = docs.reduce((a, d) => a + d.n, 0) / Math.max(1, docs.length);
    m._ch = Object.fromEntries(m.chapters.map((c) => [c.id, c]));
    return m;
  }
  // plain "where do I start?" questions go to the first-hour page, not every topic with the word "start"
  const START = /^\W*(where|how)( do| should| can)? (i|we) (start|begin)\W*$|\bget(ting)? started\b|\bmy first (time|hour|day)\b|^\W*(por d[oó]nde|c[oó]mo) (empiezo|comienzo)\W*$/i;
  function search(m, q, k = 8) {
    const qs = [...new Set(tok(q).flatMap((w) => [w, ...(SYN[w] || []).map(stem)]))];
    if (!qs.length) return [];
    const N = m._docs.length;
    return m._docs.map((d) => {
      let s = 0;
      for (const w of qs) {
        const f = d.f[w]; if (!f) continue;
        const idf = Math.log(1 + (N - m._df[w] + 0.5) / (m._df[w] + 0.5));
        s += idf * (f * 2.2) / (f + 1.2 * (0.25 + 0.75 * d.n / m._avg));
      }
      if (START.test(q) && d.c.id === "welcome" && d.t.id === "your-first-hour") s += 100;
      return { d, s };
    }).filter((r) => r.s > 0).sort((a, b) => b.s - a.s).slice(0, k)
      .map(({ d }) => ({ chapter: d.c.id, chapter_title: d.c.title, topic: d.t.id, title: d.t.title, view: d.c.view, body: d.t.body }));
  }

  /* ---------- Settings › Library view ---------- */
  const st = { c: "", t: "", q: "" };
  const goBtn = (view) => (view ? `<button type="button" class="btn btn-sm" data-lib-go="${esc(view)}">➜ ${esc(t("lib_go"))}</button>` : "");
  const topicLink = (c, tp, label) => `<a href="#" data-lib-c="${esc(c)}" data-lib-t="${esc(tp || "")}">${esc(label)}</a>`;

  function toc(m) {
    return `<aside class="lib-toc card"><h2>${esc(t("lib_contents"))}</h2>
      <p class="muted">${m.chapters.length} ${esc(t("lib_chapters"))} · ${m._docs.length} ${esc(t("lib_topics"))}</p>
      ${m.sections.map((s) => `<h3>${esc(s)}</h3><ul>${m.chapters.filter((c) => c.section === s)
        .map((c) => `<li class="${st.c === c.id ? "on" : ""}">${topicLink(c.id, "", c.title)}</li>`).join("")}</ul>`).join("")}</aside>`;
  }
  function searchBar() {
    return `<form class="lib-search" id="lib-search" role="search"><input id="lib-q" type="search" autocomplete="off" value="${esc(st.q)}" placeholder="${esc(t("lib_search_ph"))}" aria-label="${esc(t("lib_search_ph"))}" />
      <button type="submit" class="btn btn-primary">${esc(t("lib_search"))}</button>
      <button type="button" class="btn" data-help-open>💬 ${esc(t("lib_ask"))}</button></form>`;
  }
  function aiBox() {
    return ai.on
      ? `<div class="alert alert-ok lib-ai">🤖 ${esc(tf("help_mode_ai", { label: aiName() }))}</div>`
      : `<div class="alert alert-info lib-ai">${esc(t("help_connect"))} <button type="button" class="btn btn-sm" data-lib-go="ai">✨ ${esc(t("tab_ai"))}</button></div>`;
  }
  async function renderLibrary() {
    const root = document.getElementById("library-root");
    if (!root) return;
    let m;
    try { m = await manual(); } catch (e) { root.innerHTML = `<div class="alert alert-error">${esc(e.message)}</div>`; return; }
    let main;
    if (st.q) {
      const hits = search(m, st.q, 12);
      main = `<div class="card"><h2>${hits.length} ${esc(t("lib_results"))} “${esc(st.q)}”</h2>${hits.length ? `<ul class="lib-hits">${hits.map((h) =>
        `<li>${topicLink(h.chapter, h.topic, h.title)} <span class="muted">· ${esc(h.chapter_title)}</span><div class="muted">${esc(plain(h.body).slice(0, 180))}…</div></li>`).join("")}</ul>`
        : `<p class="muted">${esc(t("lib_none"))}</p>`}<p><a href="#" data-lib-home>← ${esc(t("lib_back"))}</a></p></div>`;
    } else if (st.c && m._ch[st.c]) {
      const c = m._ch[st.c];
      main = `<div class="card lib-doc"><p class="muted"><a href="#" data-lib-home>${esc(t("lib_back"))}</a> › ${esc(c.section)}</p>
        <div class="panel-head-row"><h2>${esc(c.title)}</h2>${goBtn(c.view)}</div><p class="muted">${esc(c.summary)}</p>
        <p class="lib-jump">${c.topics.map((x) => topicLink(c.id, x.id, x.title)).join(" · ")}</p>
        ${c.topics.map((x) => `<section id="lib-t-${esc(x.id)}" class="lib-topic ${st.t === x.id ? "on" : ""}"><h3>${esc(x.title)}</h3>${md(x.body)}
          <p><button type="button" class="btn btn-sm" data-help-ask="${esc(x.title)}" data-help-ref="${esc(c.id + "/" + x.id)}">💬 ${esc(t("lib_explain"))}</button></p></section>`).join("")}</div>`;
    } else {
      main = `<div class="card"><h2>${esc(m.title)}</h2><p>${esc(m.intro)}</p>${aiBox()}</div>
        <div class="card"><h2>${esc(t("lib_paths"))}</h2><div class="lib-paths">${m.paths.map((p, i) => `<div class="lib-path"><h3>${esc(p.title)}</h3><p class="muted">${esc(p.blurb)}</p>
          <ol>${p.items.map((it) => `<li>${topicLink(it.chapter, it.topic, it.label)}</li>`).join("")}</ol>
          <button type="button" class="btn btn-sm btn-primary" data-help-tour="${i}">🎓 ${esc(t("lib_teach"))}</button></div>`).join("")}</div></div>
        ${m.sections.map((s) => `<div class="card"><h2>${esc(s)}</h2><div class="lib-chaps">${m.chapters.filter((c) => c.section === s).map((c) =>
          `<a href="#" class="lib-chap" data-lib-c="${esc(c.id)}" data-lib-t=""><b>${esc(c.title)}</b><span>${esc(c.summary)}</span><small class="muted">${c.topics.length} ${esc(t("lib_topics"))}</small></a>`).join("")}</div></div>`).join("")}`;
    }
    root.innerHTML = `${searchBar()}<div class="lib-grid">${toc(m)}<div class="lib-main">${main}</div></div>`;
    if (st.t) { const el = document.getElementById("lib-t-" + st.t); if (el) el.scrollIntoView({ block: "start" }); }
  }
  function openTopic(c, tp) {
    st.c = c; st.t = tp || ""; st.q = "";
    if (O().currentView !== "library") O().showView("library"); else renderLibrary();
  }

  /* ---------- Help tutor ---------- */
  const help = { open: false, log: [], busy: false, tour: null, lastRefs: [] };
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let voiceOn = false;
  try { voiceOn = localStorage.getItem("osft_help_voice") === "1"; } catch (_) { /* private mode */ }
  const box = document.createElement("div");
  box.className = "help-w";
  box.setAttribute("translate", "no");

  function speak(text) {
    if (!voiceOn || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(plain(text).slice(0, 1200));
    u.lang = lang() === "es" ? "es-US" : "en-US";
    const v = window.speechSynthesis.getVoices().find((x) => x.lang && x.lang.toLowerCase().startsWith(lang()));
    if (v) u.voice = v;
    window.speechSynthesis.speak(u);
  }
  const srcLinks = (src) => (src && src.length ? `<div class="help-src">${src.slice(0, 3).map((s) =>
    `<a href="#" data-lib-c="${esc(s.chapter)}" data-lib-t="${esc(s.topic)}">📖 ${esc(s.chapter_title)} › ${esc(s.title)}</a>`).join("")}</div>` : "");

  function drawHelp() {
    document.body.classList.toggle("help-open", help.open);
    const hello = ai.on ? t("help_hello_ai") : t("help_hello");
    const mode = ai.on ? tf("help_mode_ai", { label: aiName() }) : t("help_mode_free");
    box.innerHTML = (help.open ? `<div class="help-p" role="dialog" aria-label="${esc(t("help_btn"))}">
      <div class="help-hd"><div><b>${esc(t("help_btn"))}</b><div class="help-mode">${esc(mode)}</div></div>
        <div class="help-tools"><label class="help-voice" title="${esc(t("help_voice_on"))}"><input type="checkbox" id="help-voice" ${voiceOn ? "checked" : ""}/> 🔊 ${esc(t("help_voice_short"))}</label>
        <button type="button" class="btn btn-sm" id="help-x">${esc(t("help_close"))}</button></div></div>
      <div class="help-log" id="help-log" aria-live="polite">
        ${help.log.length ? "" : `<div class="help-bot">${esc(hello)}${ai.on ? "" : `<div class="help-note">${esc(t("help_connect"))}</div>`}
          <div class="help-chips">${["help_suggest_1", "help_suggest_2", "help_suggest_3"].map((k) => `<button type="button" class="help-chip" data-help-ask="${esc(t(k))}">${esc(t(k))}</button>`).join("")}</div></div>`}
        ${help.log.map((m) => (m.me ? `<div class="help-me">${esc(m.me)}</div>` : `<div class="help-bot">${m.html}${srcLinks(m.src)}${m.go ? `<div class="help-acts">${goBtn(m.go)}${m.next ? `<button type="button" class="btn btn-sm btn-primary" data-help-next>${esc(t("help_next"))} ›</button>` : ""}</div>` : ""}</div>`)).join("")}
        ${help.busy ? `<div class="help-bot help-busy">${esc(t("help_thinking"))}</div>` : ""}</div>
      <form class="help-f" id="help-f">${SR ? `<button type="button" class="btn btn-sm" id="help-mic" title="${esc(t("help_mic"))}" aria-label="${esc(t("help_mic"))}">🎙️</button>` : ""}
        <input id="help-i" autocomplete="off" placeholder="${esc(t("help_ph"))}" aria-label="${esc(t("help_ph"))}" />
        <button class="btn btn-primary" ${help.busy ? "disabled" : ""}>${esc(t("help_ask_btn"))}</button></form></div>` : "") +
      `<button type="button" class="help-b" id="help-b" aria-expanded="${help.open}"><span aria-hidden="true">${help.open ? "✕" : "?"}</span> ${esc(help.open ? t("help_close") : t("help_btn"))}</button>`;
    box.querySelector("#help-b").onclick = () => toggleHelp(!help.open);
    if (!help.open) return;
    box.querySelector("#help-x").onclick = () => toggleHelp(false);
    box.querySelector("#help-voice").onchange = (e) => {
      voiceOn = e.target.checked;
      try { localStorage.setItem("osft_help_voice", voiceOn ? "1" : "0"); } catch (_) { /* private mode */ }
      if (!voiceOn && window.speechSynthesis) window.speechSynthesis.cancel();
    };
    box.querySelector("#help-f").onsubmit = (e) => { e.preventDefault(); const v = box.querySelector("#help-i").value.trim(); if (v && !help.busy) ask(v); };
    const mic = box.querySelector("#help-mic");
    if (mic) mic.onclick = () => listen(mic);
    const log = box.querySelector("#help-log"); log.scrollTop = log.scrollHeight;
    box.querySelector("#help-i").focus();
  }
  async function toggleHelp(open) {
    help.open = open;
    if (!open && window.speechSynthesis) window.speechSynthesis.cancel();
    if (open) { try { await manual(true); } catch (_) { /* shown on ask */ } } // picks up AI switched on/off in Settings
    drawHelp();
  }
  function listen(btn) {
    const rec = new SR();
    rec.lang = lang() === "es" ? "es-US" : "en-US";
    rec.interimResults = false;
    btn.classList.add("listening");
    rec.onresult = (ev) => { const said = ev.results[0][0].transcript.trim(); if (said) ask(said); };
    rec.onend = () => btn.classList.remove("listening");
    rec.onerror = () => btn.classList.remove("listening");
    try { rec.start(); } catch (_) { btn.classList.remove("listening"); }
  }
  function localAnswer(hits) {
    if (!hits.length) return { html: `<p>${esc(t("help_none"))}</p>`, text: t("help_none"), src: [] };
    const top = hits[0];
    const html = `<p>${esc(t("help_from_lib"))} <b>${esc(top.title)}</b> <span class="muted">(${esc(top.chapter_title)})</span></p>${md(top.body)}`;
    return { html, text: top.title + ". " + top.body, src: hits.slice(0, 3), go: top.view };
  }
  async function ask(q, refs) {
    help.tour = null;
    help.open = true;
    help.log.push({ me: q });
    help.busy = true; drawHelp();
    let m;
    try { m = await manual(); } catch (e) { help.busy = false; help.log.push({ html: `<p>${esc(e.message)}</p>` }); drawHelp(); return; }
    const hits = search(m, q, 5);
    // a follow-up ("and then?") rarely has words of its own: keep the pages from the question before it
    const ids = [...new Set([...(refs || []), ...hits.slice(0, 4).map((h) => h.chapter + "/" + h.topic), ...help.lastRefs])].slice(0, 6);
    help.lastRefs = ids.slice(0, 3);
    let out = null;
    if (ai.on) {
      try {
        const history = [];
        for (let i = 0; i + 1 < help.log.length - 1; i++) if (help.log[i].me && help.log[i + 1].text) history.push({ q: help.log[i].me, a: help.log[i + 1].text });
        const r = await O().api("/api/library/ask", { method: "POST", body: JSON.stringify({ question: q, lang: lang(), refs: ids, history: history.slice(-4), view: O().currentView }) });
        if (r.mode === "ai" && r.answer) out = { html: md(r.answer), text: r.answer, src: r.sources, go: hits[0] && hits[0].view };
        else if (r.mode === "off") ai = { on: false, label: "", provider: "" };
      } catch (e) {
        out = localAnswer(hits);
        out.html = `<p class="help-note">${esc(tf("help_ai_failed", { e: e.message }))}</p>` + out.html;
      }
    }
    if (!out) out = localAnswer(hits);
    help.busy = false;
    help.log.push(out);
    drawHelp();
    speak(out.text);
  }
  async function tour(i, step) {
    const m = await manual();
    const p = m.paths[i]; if (!p) return;
    if (!help.open) { help.open = true; }
    if (step === 0) help.log.push({ me: "🎓 " + p.title });
    const it = p.items[step];
    if (!it) { help.tour = null; help.log.push({ html: `<p>${esc(t("help_done"))}</p>`, text: t("help_done") }); drawHelp(); speak(t("help_done")); return; }
    const c = m._ch[it.chapter];
    const tps = it.topic ? c.topics.filter((x) => x.id === it.topic) : c.topics.slice(0, 1);
    const body = tps.map((x) => md(x.body)).join("");
    help.tour = { i, step };
    help.log.forEach((x) => (x.next = false));
    help.log.push({ html: `<p class="help-step">${esc(tf("help_step", { n: step + 1, total: p.items.length }))}: <b>${esc(it.label)}</b></p>${body}`,
      text: it.label + ". " + tps.map((x) => x.body).join(" "), src: [{ chapter: c.id, chapter_title: c.title, topic: tps[0] ? tps[0].id : "", title: it.label }], go: c.view || "home", next: true });
    drawHelp();
    speak(help.log[help.log.length - 1].text);
  }

  /* ---------- wiring ---------- */
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-lib-c]");
    if (a) { e.preventDefault(); openTopic(a.dataset.libC, a.dataset.libT); return; }
    const go = e.target.closest("[data-lib-go]");
    if (go) { e.preventDefault(); O().showView(go.dataset.libGo); return; }
    if (e.target.closest("[data-lib-home]")) { e.preventDefault(); openTopic("", ""); return; }
    const q = e.target.closest("[data-help-ask]");
    if (q) { e.preventDefault(); ask(q.dataset.helpAsk, q.dataset.helpRef ? [q.dataset.helpRef] : []); return; }
    const tr = e.target.closest("[data-help-tour]");
    if (tr) { e.preventDefault(); tour(+tr.dataset.helpTour, 0); return; }
    if (e.target.closest("[data-help-next]") && help.tour) { e.preventDefault(); tour(help.tour.i, help.tour.step + 1); return; }
    if (e.target.closest("[data-help-open]")) { e.preventDefault(); toggleHelp(true); return; }
  });
  document.addEventListener("submit", (e) => {
    if (e.target.id !== "lib-search") return;
    e.preventDefault();
    st.q = document.getElementById("lib-q").value.trim(); st.c = ""; st.t = "";
    renderLibrary();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && help.open) toggleHelp(false); });

  function boot() {
    if (!window.OSFT || !O().registerView) return setTimeout(boot, 50);
    O().registerView("library", async () => { try { await manual(true); } catch (_) { /* rendered below */ } renderLibrary(); });
    document.body.appendChild(box);
    drawHelp();
    // app.js sets <html lang> every time it applies a language (first load and every EN/ES tap): re-draw then
    let shown = "";
    new MutationObserver(async () => {
      const l = lang() + "|" + t("help_btn");
      if (l === shown) return;
      shown = l;
      try { await manual(); } catch (_) { /* login screen */ }
      if (O().currentView === "library") renderLibrary();
      drawHelp();
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    manual().then(drawHelp).catch(() => { /* login screen: Help still opens */ });
  }
  window.OSFT_LIBRARY = { search: (q) => manual().then((m) => search(m, q)), ask, open: () => toggleHelp(true), tour: (i) => tour(i, 0) };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
