/* OSFT first-party analytics beacon: no cookies, no third parties. Honors Do Not Track. */
(function () {
  var dnt = navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl === true;
  function send(e, extra) {
    if (dnt) return;
    var d = { e: e, u: location.pathname + location.search, r: document.referrer || "", l: document.documentElement.lang || "en" };
    for (var k in (extra || {})) d[k] = extra[k];
    var body = JSON.stringify(d);
    try {
      if (navigator.sendBeacon && navigator.sendBeacon("/api/collect", new Blob([body], { type: "application/json" }))) return;
    } catch (x) {}
    try { fetch("/api/collect", { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true }); } catch (x) {}
  }
  window.osftBeacon = send;
  send("pageview");
})();
