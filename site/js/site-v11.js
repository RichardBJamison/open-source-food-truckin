(function () {
  "use strict";

  function dict() {
    return window.OSFT_I18N || { en: {}, es: {} };
  }

  function cookieLang() {
    var m = document.cookie.match(/(?:^|;\s*)osft_lang=(en|es)(?:;|$)/);
    return m ? m[1] : "";
  }

  function saveLang(locale) {
    try { localStorage.setItem("osft_lang", locale); } catch (e) {}
    try {
      document.cookie = "osft_lang=" + locale + ";path=/;max-age=31536000;SameSite=Lax";
    } catch (e) {}
  }

  function readLang() {
    try {
      var q = /(?:^|[?&])lang=(en|es)(?:&|$)/.exec(location.search);
      if (q) return q[1];
      var s = localStorage.getItem("osft_lang");
      if (s === "es" || s === "en") return s;
    } catch (e) {}
    var c = cookieLang();
    if (c) return c;
    return "en";
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
    if (!fromPack || !toPack || !document.body) return;
    var map = {};
    Object.keys(fromPack).forEach(function (k) {
      var a = fromPack[k];
      var b = toPack[k];
      if (typeof a !== "string" || typeof b !== "string") return;
      if (!a || a === b) return;
      map[a] = b;
    });
    var skip = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, CODE: 1 };
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        var p = node.parentElement;
        if (!p || skip[p.tagName]) return NodeFilter.FILTER_REJECT;
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var pending = [];
    var node;
    while ((node = walker.nextNode())) pending.push(node);
    pending.forEach(function (n) {
      var raw = n.nodeValue;
      var trimmed = raw.replace(/\s+/g, " ").trim();
      var next = map[raw] || map[trimmed];
      if (next) n.nodeValue = raw.indexOf(trimmed) >= 0 ? raw.replace(trimmed, next) : next;
    });
  }

  function withLang(href, locale) {
    if (!href) return href;
    if (/^(https?:|mailto:|tel:|javascript:)/i.test(href)) return href;
    if (href.charAt(0) === "#") return href;
    var hash = "";
    var h = href.indexOf("#");
    if (h >= 0) {
      hash = href.slice(h);
      href = href.slice(0, h);
    }
    href = href.replace(/([?&])lang=(en|es)(&|$)/g, function (_, sep, _l, end) {
      return end === "&" ? sep : "";
    }).replace(/[?&]$/, "");
    if (locale === "es") {
      href += (href.indexOf("?") >= 0 ? "&" : "?") + "lang=es";
    }
    return href + hash;
  }

  function stampLinks(locale) {
    document.querySelectorAll("a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href) return;
      if (/^(https?:|mailto:|tel:|javascript:)/i.test(href) && href.indexOf(location.host) === -1) return;
      if (href.indexOf("127.0.0.1:5054") !== -1 || href.indexOf("localhost:5054") !== -1) {
        try {
          var u = new URL(href, location.href);
          if (locale === "es") u.searchParams.set("lang", "es");
          else u.searchParams.delete("lang");
          a.setAttribute("href", u.toString());
        } catch (e) {}
        return;
      }
      a.setAttribute("href", withLang(href, locale));
    });
  }

  function apply(lang) {
    var all = dict();
    var locale = (lang === "es" || lang === "en") ? lang : "en";
    if (!all[locale] || !Object.keys(all[locale] || {}).length) {
      locale = all.es && Object.keys(all.es).length ? locale : "en";
    }
    var pack = all[locale] || {};
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

    if (locale === "es") walkText(all.en, pack);
    else walkText(all.es, all.en);

    document.querySelectorAll(".lang button").forEach(function (btn) {
      var on = btn.getAttribute("data-locale") === locale;
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var langGroup = document.querySelector(".lang");
    if (langGroup && pack.lang) langGroup.setAttribute("aria-label", pack.lang);

    stampLinks(locale);

    document.querySelectorAll("iframe.lot-frame").forEach(function (frame) {
      try {
        var u = new URL(frame.getAttribute("src") || frame.src, location.href);
        if (locale === "es") u.searchParams.set("lang", "es");
        else u.searchParams.delete("lang");
        var next = u.toString();
        if (frame.src !== next) frame.src = next;
      } catch (e) {}
    });

    saveLang(locale);
    document.documentElement.classList.remove("osft-i18n-wait");
  }

  function boot() {
    apply(readLang());
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest(".lang button");
    if (btn) {
      e.preventDefault();
      apply(btn.getAttribute("data-locale"));
      return;
    }
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;
    var href = a.getAttribute("href");
    if (!href || href.charAt(0) === "#") return;
    if (/^(mailto:|tel:|javascript:)/i.test(href)) return;
    if (/^https?:/i.test(href) && href.indexOf(location.host) === -1 && href.indexOf(":5054") === -1) return;
    var locale = document.documentElement.lang === "es" ? "es" : "en";
    var next = withLang(href, locale);
    if (next !== href) a.setAttribute("href", next);
  }, true);

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
