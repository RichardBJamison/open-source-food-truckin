/* Settings thank-you popup + IHS / Reservation Relief pitch (mirrors Open Source Barware settings promo).
   Opens each time Settings (view-setup) is shown, unless "Do not open again" was ticked (localStorage). */
(function () {
  "use strict";
  var KEY = "osft_promo_hide";
  var modal = document.getElementById("promo-modal");
  var view = document.getElementById("view-setup");
  if (!modal || !view) return;
  var box = document.getElementById("promo-dont-show");
  var lastFocus = null, shownThisVisit = false;
  function hidden() { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function open(force) {
    if (!force && hidden()) return;
    box.checked = hidden();
    lastFocus = document.activeElement;
    modal.classList.remove("hidden");
    document.getElementById("promo-close").focus();
  }
  function close() {
    try { if (box.checked) localStorage.setItem(KEY, "1"); else localStorage.removeItem(KEY); } catch (e) {}
    modal.classList.add("hidden");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  document.getElementById("promo-close").addEventListener("click", close);
  document.getElementById("promo-close-x").addEventListener("click", close);
  modal.addEventListener("click", function (e) { if (e.target === modal) close(); });
  document.addEventListener("keydown", function (e) {
    if (modal.classList.contains("hidden")) return;
    if (e.key === "Escape") { e.preventDefault(); close(); return; }
    if (e.key === "Tab") { // keep focus inside the dialog
      var f = modal.querySelectorAll("a[href],button,input");
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  var re = document.getElementById("promo-reopen");
  if (re) re.addEventListener("click", function () { open(true); });
  function check() {
    var on = !view.classList.contains("hidden");
    if (on && !shownThisVisit) { shownThisVisit = true; open(false); }
    if (!on) shownThisVisit = false;
  }
  new MutationObserver(check).observe(view, { attributes: true, attributeFilter: ["class"] });
  check();
  window.OSFT_PROMO = { open: function () { open(true); }, KEY: KEY };
})();
