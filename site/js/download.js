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
        thanks(os, d.url);
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


  var TY = {
    en: { h: "Thank you.", sub: "Open Source Food Truckin' is on its way", lead: "Your zip is saving now. Here is exactly what to do next:",
      mac: ["Double-click the zip in Downloads. You get the folder <b>open-source-food-truckin-program</b>.",
            "Open START-HERE-MAC.html in that folder (it shows every step), or double-click <b>Install.command</b>.",
            "Mac says it can't verify it? Click Done, open <b>System Settings › Privacy &amp; Security</b>, click <b>Open Anyway</b>, double-click Install.command again.",
            "Asked to install developer tools? Click Install, then run Install.command again.",
            "Your browser opens <b>http://127.0.0.1:5053/</b>. Bookmark it — that bookmark is the software."],
      win: ["Right-click the zip › <b>Extract All</b>. Open the folder <b>open-source-food-truckin-program</b>.",
            "Double-click <b>Install.bat</b> (not install.ps1).",
            "“Windows protected your PC”? Click <b>More info › Run anyway</b>.",
            "No Python? It opens python.org — install with <b>Add python.exe to PATH</b> checked, then run Install.bat again.",
            "Your browser opens <b>http://127.0.0.1:5053/</b>. Bookmark it — that bookmark is the software."],
      more: "Full guide: README-INSTALL.txt inside the folder.", again: "Download didn't start? Click here.", ok: "Keep rolling",
      rr: "From the same house: Reservation Relief and IHS build your restaurant or truck website — $300, Nexus included." },
    es: { h: "Gracias.", sub: "Open Source Food Truckin' va en camino", lead: "Tu zip se está guardando. Esto es lo que sigue:",
      mac: ["Doble clic en el zip en Descargas. Aparece la carpeta <b>open-source-food-truckin-program</b>.",
            "Abre START-HERE-MAC.html en esa carpeta (muestra cada paso), o haz doble clic en <b>Install.command</b>.",
            "¿El Mac no lo puede verificar? Clic en OK, abre <b>Ajustes del Sistema › Privacidad y seguridad</b>, clic en <b>Abrir igualmente</b> y vuelve a abrir Install.command.",
            "¿Pide herramientas de desarrollo? Clic en Instalar y vuelve a correr Install.command.",
            "Se abre <b>http://127.0.0.1:5053/</b>. Guárdalo en favoritos: ese favorito es el software."],
      win: ["Clic derecho en el zip › <b>Extraer todo</b>. Abre la carpeta <b>open-source-food-truckin-program</b>.",
            "Doble clic en <b>Install.bat</b> (no install.ps1).",
            "¿“Windows protegió su PC”? <b>Más información › Ejecutar de todas formas</b>.",
            "¿Sin Python? Se abre python.org: instálalo marcando <b>Add python.exe to PATH</b> y vuelve a correr Install.bat.",
            "Se abre <b>http://127.0.0.1:5053/</b>. Guárdalo en favoritos: ese favorito es el software."],
      more: "Guía completa: README-INSTALL.txt dentro de la carpeta.", again: "¿No empezó la descarga? Haz clic aquí.", ok: "Sigue rodando",
      rr: "De la misma casa: Reservation Relief e IHS construyen tu sitio web — $300, Nexus incluido." }
  };
  function thanks(os, url) {
    var L = TY[lang()], old = document.getElementById("dl-thanks");
    if (old) old.remove();
    var steps = (os === "win" ? L.win : L.mac).map(function (x) { return "<li>" + x + "</li>"; }).join("");
    var m = document.createElement("div");
    m.id = "dl-thanks"; m.className = "dl-thanks"; m.setAttribute("role", "dialog"); m.setAttribute("aria-modal", "true");
    m.innerHTML = '<div class="dl-thanks-card"><button type="button" class="dl-thanks-x" aria-label="Close">×</button>' +
      "<h2>" + L.h + "</h2><p class=\"dl-thanks-sub\">" + L.sub + " — " + (os === "win" ? "Windows" : "Mac") + "</p>" +
      "<p>" + L.lead + "</p><ol>" + steps + "</ol><p class=\"dl-thanks-more\">" + L.more +
      ' <a href="' + url + '">' + L.again + "</a></p>" +
      '<p class="dl-thanks-rr">' + L.rr + ' <a href="https://www.reservationrelief.com/" target="_blank" rel="noopener">reservationrelief.com</a> · <a href="https://intelligenthospitalitysystems.com/" target="_blank" rel="noopener">IHS</a></p>' +
      '<button type="button" class="dl-thanks-ok">' + L.ok + "</button></div>";
    function close() { m.remove(); document.body.style.overflow = ""; }
    m.addEventListener("click", function (e) { if (e.target === m || e.target.closest(".dl-thanks-x,.dl-thanks-ok")) close(); });
    document.addEventListener("keydown", function k(e) { if (e.key === "Escape") { close(); document.removeEventListener("keydown", k); } });
    document.body.appendChild(m); document.body.style.overflow = "hidden";
  }

  // keep the status line in the chosen language when EN/ES is flipped
  new MutationObserver(function () {
    var key = msg.getAttribute("data-key");
    if (key) msg.textContent = t(key);
  }).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });

  loadCount();
  setInterval(loadCount, 60000);
})();
