/* Download page: email gate + "Trucks rolling" counter. Talks to serve_site.py (/api/download, /api/download-count). */
(function () {
  "use strict";

  var form = document.getElementById("dl-form");
  var input = document.getElementById("dl-email");
  var msg = document.getElementById("dl-msg");
  var board = document.getElementById("dl-count");
  if (!form || !input || !board) return;

  var EMAIL = /^[^@\s<>"',;]+@[^@\s<>"',;]+\.[A-Za-z]{2,}$/;
  var DIGITS = 6;
  var shown = null;

  function lang() { return document.documentElement.lang === "es" ? "es" : "en"; }
  function t(key) {
    var all = window.OSFT_I18N || {};
    return (all[lang()] || {})[key] || (all.en || {})[key] || key;
  }
  function say(key, kind) {
    msg.textContent = t(key);
    msg.setAttribute("data-key", key);
    msg.className = "dl-msg" + (kind ? " is-" + kind : "");
  }

  function paint(total) {
    var s = String(Math.max(0, total | 0));
    while (s.length < DIGITS) s = "0" + s;
    var old = board.querySelectorAll("span");
    var spans = "";
    for (var i = 0; i < s.length; i++) {
      var changed = shown !== null && (!old[i] || old[i].textContent !== s[i]);
      spans += '<span' + (changed ? ' class="is-flip"' : "") + ">" + s[i] + "</span>";
    }
    board.innerHTML = spans;
    board.setAttribute("aria-label", total + " " + t("dl_count_cap"));
    shown = total;
  }

  function loadCount() {
    fetch("/api/download-count", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d && typeof d.total === "number") paint(d.total); })
      .catch(function () {});
  }

  try { input.value = localStorage.getItem("osft_dl_email") || ""; } catch (e) {}
  if (/[?&]expired=1/.test(location.search)) say("dl_expired", "warn");

  var chosen = "mac";
  form.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("button[name=os]");
    if (b) chosen = b.value;
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var os = (e.submitter && e.submitter.value) || chosen;
    var email = input.value.trim();
    if (!EMAIL.test(email)) {
      say("dl_err_email", "warn");
      input.focus();
      return;
    }
    var hp = form.querySelector(".dl-hp");
    form.classList.add("is-busy");
    fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, os: os, lang: lang(), website: hp ? hp.value : "" })
    })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { d.status = r.status; return d; }); })
      .then(function (d) {
        form.classList.remove("is-busy");
        if (!d.ok) {
          say(d.error === "email" ? "dl_err_email" : d.error === "busy" ? "dl_err_busy" : "dl_err_net", "warn");
          return;
        }
        try { localStorage.setItem("osft_dl_email", email); } catch (e2) {}
        if (typeof d.total === "number") paint(d.total);
        say("dl_ok", "ok");
        document.querySelectorAll(".dl-steps [data-os]").forEach(function (el) {
          el.classList.toggle("is-mine", el.getAttribute("data-os") === os);
        });
        if (window.OfferTracker) { try { window.OfferTracker.emit("download", { os: os }); } catch (e3) {} }
        window.location.href = d.url;
        setTimeout(function () {
          var steps = document.getElementById("install-steps");
          if (steps) steps.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 900);
      })
      .catch(function () {
        form.classList.remove("is-busy");
        say("dl_err_net", "warn");
      });
  });

  // keep the status line in the chosen language when EN/ES is flipped
  new MutationObserver(function () {
    var key = msg.getAttribute("data-key");
    if (key) msg.textContent = t(key);
  }).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });

  loadCount();
  setInterval(loadCount, 60000);
})();
