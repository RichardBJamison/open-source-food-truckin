"""Settings › Library and the Help tutor."""
import json
import re

import server
from osft import accounts as acct
from osft import library as lib

from conftest import ROOT


def test_manual_has_no_broken_links_and_languages_match():
    assert lib.problems(ROOT / "library") == []


def test_every_chapter_view_is_a_real_screen():
    app_js = (ROOT / "static/js/app.js").read_text()
    groups = re.search(r"const GROUPS = \{(.*?)\};", app_js, re.S).group(1)
    views = set(re.findall(r'"([a-z]+)"', groups))
    html = (ROOT / "static/index.html").read_text()
    for lang in lib.LANGS:
        for c in lib.load(ROOT / "library", lang)["chapters"]:
            assert c["view"] in views, (lang, c["id"], c["view"])
            assert f'id="view-{c["view"]}"' in html


def test_library_tab_sits_under_settings():
    app_js = (ROOT / "static/js/app.js").read_text()
    assert '"data", "library"]' in app_js and 'library: ["tab_library", "📖"]' in app_js
    assert '<script src="/static/js/library.js"></script>' in (ROOT / "static/index.html").read_text()


def test_get_manual_both_languages(client):
    en = client.get("/api/library/en").get_json()
    es = client.get("/api/library/es").get_json()
    assert en["ok"] and es["ok"]
    assert len(en["manual"]["chapters"]) == len(es["manual"]["chapters"]) >= 20
    assert en["manual"]["sections"][0] == "Start here" and es["manual"]["sections"][0] == "Empieza aquí"
    assert en["ai"] == {"on": False, "label": "", "provider": ""}
    assert client.get("/api/library/fr").get_json()["manual"]["lang"] == "en"
    # spanish topic ids are the english ones, headings are spanish
    t0 = es["manual"]["chapters"][0]["topics"][0]
    assert t0["id"] == "what-this-program-is" and t0["title"] == "Qué es este programa" and "{#" not in json.dumps(es)


def test_ask_needs_a_question(client):
    r = client.post("/api/library/ask", json={"question": "  "})
    assert r.status_code == 400


def test_ask_with_ai_off_never_calls_ai(client, monkeypatch):
    monkeypatch.setattr(server.ai_mod, "chat", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    r = client.post("/api/library/ask", json={"question": "how do I count?", "lang": "en"}).get_json()
    assert r == {"ok": True, "mode": "off"}


def _ai_on(client):
    r = client.put("/api/ai/settings", json={"provider": "custom", "base_url": "http://127.0.0.1:9/v1", "model": "m",
                                             "api_key": "sk-secret-123456", "enabled": True})
    assert r.status_code == 200, r.get_json()


def test_ask_with_ai_on_sends_pages_and_truck_summary(seeded, monkeypatch):
    _ai_on(seeded)
    seen = {}

    def fake_chat(cfg, content, **kw):
        seen["prompt"], seen["kw"] = content, kw
        return "1. Open **Inventory sheets › Count sheet**.\n2. Press **Start count walk**."

    monkeypatch.setattr(server.ai_mod, "chat", fake_chat)
    assert seeded.get("/api/library/en").get_json()["ai"]["on"] is True
    r = seeded.post("/api/library/ask", json={"question": "Como cuento el camion?", "lang": "es",
                                              "refs": ["counting/start-a-count", "nope/x", 7], "view": "count",
                                              "history": [{"q": "hola", "a": "hola!"}]}).get_json()
    assert r["mode"] == "ai" and r["answer"].startswith("1. Open")
    assert r["sources"] == [{"chapter": "counting", "chapter_title": "Contar el camión", "topic": "start-a-count",
                             "title": "Iniciar un conteo"}]
    p = seen["prompt"]
    assert "Responde en español." in p and "Iniciar un conteo" in p and "QUESTION:\nComo cuento el camion?" in p
    assert "'count' screen" in p and "User: hola" in p
    snap = json.loads(p.split("TRUCK SUMMARY (read-only):\n", 1)[1].split("\n\n", 1)[0])
    assert snap["products"] > 0 and snap["ai_on"] is True and "below_par" in snap
    assert "sk-secret-123456" not in p and "pin" not in p.lower().replace("pinned", "")
    assert seen["kw"]["want_json"] is False


def test_ask_falls_back_to_welcome_and_reports_ai_errors(client, monkeypatch):
    _ai_on(client)
    seen = {}

    def boom(cfg, content, **kw):
        seen["p"] = content
        raise server.ai_mod.AIError("The AI service said 401")

    monkeypatch.setattr(server.ai_mod, "chat", boom)
    r = client.post("/api/library/ask", json={"question": "hi"})
    assert r.status_code == 502 and "401" in r.get_json()["error"]
    assert "What this program is" in seen["p"]


def test_library_is_open_to_every_login():
    for path, method in (("/api/library/en", "GET"), ("/api/library/es", "GET"), ("/api/library/ask", "POST")):
        assert acct.required_perm(path, method) is None


def test_snapshot_has_no_secrets(seeded):
    _ai_on(seeded)
    with server.app.test_request_context():
        snap = server.library_snapshot()
    text = json.dumps(snap).lower()
    assert "sk-secret" not in text and "pin_hash" not in text and "@" not in text
    assert snap["sections"] and snap["completed_counts"] >= 1


def test_prompt_trims_long_input():
    p = lib.build_prompt("en", "x" * 5000, [], {}, [{"q": "q" * 900, "a": "a" * 900}] * 9)
    assert p.count("User: ") == 4 and "x" * 1000 in p and "x" * 1001 not in p
