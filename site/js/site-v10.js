(function () {
  "use strict";

  function dict() {
    return window.OSFT_I18N || { en: {}, es: {} };
  }

  function fill(el, val) {
    if (val == null || val === "") return;
    try {
      if (el.hasAttribute("data-i18n-html") || /<[a-z][\s\S]*>/i.test(val)) {
        el.innerHTML = val;
        return;
      }
      if (el.tagName === "TITLE") {
        document.title = val;
        el.textContent = val;
        return;
      }
      if (el.tagName === "META") {
        el.setAttribute("content", val);
        return;
      }
      el.textContent = val;
    } catch (e) {}
  }

  function walkText(fromPack, toPack) {
    if (!fromPack || !toPack) return;
    var map = {};
    Object.keys(fromPack).forEach(function (k) {
      var a = fromPack[k];
      var b = toPack[k];
      if (typeof a !== "string" || typeof b !== "string") return;
      if (!a || a === b) return;
      map[a] = b;
    });
    if (!document.body) return;
    var skip = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, CODE: 1 };
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        var p = node.parentElement;
        if (!p || skip[p.tagName]) return NodeFilter.FILTER_REJECT;
        var t = node.nodeValue;
        if (!t || !t.trim()) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var node;
    var pending = [];
    while ((node = walker.nextNode())) pending.push(node);
    pending.forEach(function (n) {
      var raw = n.nodeValue;
      var trimmed = raw.replace(/\s+/g, " ").trim();
      var next = map[raw] || map[trimmed];
      if (next) n.nodeValue = raw.indexOf(trimmed) >= 0 ? raw.replace(trimmed, next) : next;
    });
  }

  function apply(lang) {
    var all = dict();
    var locale = all[lang] ? lang : "en";
    var pack = all[locale] || {};
    var prev = document.documentElement.getAttribute("lang") || "en";
    document.documentElement.lang = locale;
    document.documentElement.setAttribute("data-lang", locale);

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (pack[key]) fill(el, pack[key]);
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      var key = el.getAttribute("data-i18n-html");
      if (pack[key]) {
        try { el.innerHTML = pack[key]; } catch (e) {}
      }
    });
    document.querySelectorAll("[data-i18n-content]").forEach(function (el) {
      var key = el.getAttribute("data-i18n-content");
      if (pack[key]) el.setAttribute("content", pack[key]);
    });

    if (prev !== locale) walkText(all[prev] || all.en, pack);

    document.querySelectorAll(".lang button").forEach(function (btn) {
      var on = btn.getAttribute("data-locale") === locale;
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var langGroup = document.querySelector(".lang");
    if (langGroup && pack.lang) langGroup.setAttribute("aria-label", pack.lang);

    document.querySelectorAll("iframe.lot-frame").forEach(function (frame) {
      try {
        var u = new URL(frame.getAttribute("src"), location.href);
        u.searchParams.set("lang", locale);
        var next = u.toString();
        if (frame.src !== next) frame.src = next;
      } catch (e) {}
    });

    try { localStorage.setItem("osft_lang", locale); } catch (e) {}
  }

  function boot() {
    var lang = "en";
    try {
      var q = /(?:^|[?&])lang=(en|es)(?:&|$)/.exec(location.search);
      lang = (q && q[1]) || localStorage.getItem("osft_lang") || "en";
    } catch (e) {}
    apply(lang);
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest(".lang button");
    if (!btn) return;
    e.preventDefault();
    apply(btn.getAttribute("data-locale"));
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  window.addEventListener("pageshow", boot);

  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  var heroVid = document.querySelector("video.poster-art");
  if (heroVid) {
    var motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    function kickHero() {
      heroVid.muted = true;
      heroVid.defaultMuted = true;
      heroVid.loop = true;
      heroVid.playsInline = true;
      if (motion.matches) {
        heroVid.pause();
        return;
      }
      var playPromise = heroVid.play();
      if (playPromise) playPromise.catch(function () {});
    }
    kickHero();
    heroVid.addEventListener("canplay", kickHero);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") kickHero();
    });
    if (motion.addEventListener) motion.addEventListener("change", kickHero);
  }

  window.OSFT_APPLY = apply;
})();
