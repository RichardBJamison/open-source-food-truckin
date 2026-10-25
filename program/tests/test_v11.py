"""v1.1: sections editor, onboarding order, AI settings, invoice extraction + shelf proposals (mocked AI endpoint)."""
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import server
from osft import ai, sections

CALLS = []
REPLY = {"content": "{}"}


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        CALLS.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        out = json.dumps({"choices": [{"message": {"content": REPLY["content"]}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)


@pytest.fixture(scope="module")
def mock_ai():
    srv = HTTPServer(("127.0.0.1", 0), _H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}/v1"
    srv.shutdown()


@pytest.fixture(autouse=True)
def _reset():
    CALLS.clear()


def connect(client, url):
    r = client.put("/api/ai/settings", json={"provider": "custom", "base_url": url, "model": "test-model",
                                              "api_key": "sk-secret-9999", "enabled": True})
    assert r.status_code == 200, r.json
    return r.json["ai"]


# ---------- onboarding order (matches OSBW setup.html) ----------

def test_onboarding_order_matches_osbw(client):
    ob = client.get("/api/onboarding").json
    assert ob["phases"] == ["welcome", "business", "sections", "walk", "reconcile", "review", "first_count", "account", "done"]
    assert ob["onboarding"]["phase"] == "welcome"
    assert client.put("/api/onboarding", json={"phase": "sections"}).status_code == 200
    assert client.put("/api/onboarding", json={"phase": "nope"}).status_code == 400


# ---------- sections ----------

def test_sections_default_and_custom_editor(client):
    r = client.get("/api/sections").json
    assert [s["key"] for s in r["sections"]] == ["cooler", "freezer", "dry", "prep"] and not r["custom"]
    assert any(s["name"] == "Propane rack" for s in r["suggestions"])
    r = client.put("/api/sections", json={"sections": [{"key": "cooler", "name": "Big cooler"}, "Line", "Dry shelf 1", "Cab", "Propane rack"]})
    assert r.status_code == 200, r.json
    keys = [s["key"] for s in r.json["sections"]]
    assert keys == ["cooler", "line", "dry-shelf-1", "cab", "propane-rack"]
    assert client.get("/api/zones").json["zones"] == keys
    it = client.post("/api/items", json={"name": "Propane 20 lb", "unit": "ea", "par": 2, "category": "Fuel", "zone": "propane-rack"})
    assert it.status_code == 201
    assert client.post("/api/items", json={"name": "X", "unit": "ea", "par": 1, "category": "O", "zone": "freezer"}).status_code == 400
    # reorder + rename keeps the key, product still points at it
    r = client.put("/api/sections", json={"sections": [{"key": "cooler", "name": "Big cooler"}]})
    assert r.status_code == 409
    r = client.put("/api/sections", json={"sections": [{"key": "propane-rack", "name": "Gas rack"}, {"key": "cooler", "name": "Big cooler"},
                                                       {"key": "line", "name": "Line"}, {"key": "dry-shelf-1", "name": "Dry shelf 1"}, {"key": "cab", "name": "Cab"}]})
    assert r.status_code == 200 and r.json["sections"][0] == {"key": "propane-rack", "name": "Gas rack"}
    assert client.get("/api/items").json["items"][0]["zone"] == "propane-rack"


def test_sections_delete_needs_move_and_validation(client):
    client.put("/api/sections", json={"sections": ["Cooler", "Cab"]})
    client.post("/api/items", json={"name": "Napkins", "unit": "pack", "par": 2, "category": "Paper", "zone": "cab"})
    r = client.put("/api/sections", json={"sections": [{"key": "cooler", "name": "Cooler"}]})
    assert r.status_code == 409 and r.json["needs_move"] and r.json["count"] == 1
    r = client.put("/api/sections", json={"sections": [{"key": "cooler", "name": "Cooler"}], "move_to": "cooler"})
    assert r.status_code == 200
    assert client.get("/api/items").json["items"][0]["zone"] == "cooler"
    assert client.put("/api/sections", json={"sections": []}).status_code == 400
    assert client.put("/api/sections", json={"sections": ["A", "a"]}).status_code == 400
    assert client.put("/api/sections", json={"sections": ["x" * 41]}).status_code == 400


def test_section_walk_and_count(client):
    client.put("/api/sections", json={"sections": ["Lowboy", "Dry shelf 1"]})
    r = client.post("/api/voice/walk", json={"text": "chicken thighs 3, crema 2", "section": "lowboy"}).json
    assert r["proposals"] and all(p["zone"] == "lowboy" for p in r["proposals"])
    assert client.post("/api/voice/walk", json={"text": "crema 2", "section": "nope"}).status_code == 400
    assert client.post("/api/voice/walk/apply", json={"proposals": r["proposals"]}).json["added"] >= 2
    items = client.get("/api/items").json["items"]
    assert all(i["zone"] == "lowboy" for i in items)
    c = client.post("/api/sections/lowboy/count", json={"counts": {items[0]["id"]: 7}})
    assert c.json["updated"] == 1 and client.get("/api/items").json["items"][0]["on_hand"] == 7
    assert client.post("/api/sections/lowboy/count", json={"counts": {items[0]["id"]: -1}}).status_code == 400


# ---------- AI settings ----------

def test_ai_off_by_default_never_calls(client, mock_ai):
    s = client.get("/api/ai").json
    assert s["ai"]["enabled"] is False and {p["key"] for p in s["presets"]} >= {"openai", "anthropic", "xai", "ollama", "custom"}
    client.put("/api/sections", json={"sections": ["Cooler"]})
    # configured but OFF → still no call
    client.put("/api/ai/settings", json={"provider": "custom", "base_url": mock_ai, "model": "m", "api_key": "k-123456789"})
    assert client.post("/api/ai/shelf", json={"section": "cooler", "text": "3 cases chicken"}).status_code == 409
    assert client.post("/api/ai/tidy", json={"section": "cooler", "text": "chikin"}).status_code == 409
    up = client.post("/api/invoice/upload", data={"files": (io.BytesIO(b"\x89PNG\r\n\x1a\n000"), "i.png")}, content_type="multipart/form-data")
    assert up.status_code == 201 and up.json["ai_enabled"] is False
    assert client.post("/api/ai/invoice", json={"files": [up.json["files"][0]["name"]]}).status_code == 409
    assert CALLS == []


def test_ai_settings_validation_and_key_hidden(client, mock_ai):
    assert client.put("/api/ai/settings", json={"provider": "openai", "enabled": True}).status_code == 400  # needs key
    assert client.put("/api/ai/settings", json={"provider": "bogus"}).status_code == 400
    assert client.put("/api/ai/settings", json={"provider": "custom", "base_url": "ftp://x", "model": "m"}).status_code == 400
    r = client.put("/api/ai/settings", json={"provider": "ollama", "enabled": True}).json  # local Ollama: no key needed
    assert r["ai"]["enabled"] and r["ai"]["base_url"].startswith("http://localhost:11434")
    a = connect(client, mock_ai)
    assert a["has_key"] and a["key_hint"] == "…9999"
    for path in ("/api/ai", "/api/settings/ai", "/api/settings", "/api/onboarding"):
        assert "sk-secret-9999" not in client.get(path).get_data(as_text=True)
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(client.get("/api/backup").data))
    assert not any(b"sk-secret-9999" in z.read(n) for n in z.namelist())
    REPLY["content"] = '{"ok": true}'
    t = client.post("/api/ai/test", json={})
    assert t.status_code == 200 and "ok" in t.json["reply"]
    assert CALLS[-1]["auth"] == "Bearer sk-secret-9999" and CALLS[-1]["path"] == "/v1/chat/completions"
    assert client.put("/api/ai/settings", json={"enabled": False}).json["ai"]["enabled"] is False


def test_ai_unreachable_is_clean_error(client):
    client.put("/api/sections", json={"sections": ["Cooler"]})
    connect(client, "http://127.0.0.1:9/v1")
    r = client.post("/api/ai/shelf", json={"section": "cooler", "text": "beef"})
    assert r.status_code == 502 and "reach" in r.json["error"]


# ---------- invoice extraction ----------

def test_invoice_extract_review_then_save(client, mock_ai):
    beef = client.post("/api/items", json={"name": "Ground beef", "unit": "lb", "par": 20, "category": "Protein", "zone": "cooler"}).json["item"]
    connect(client, mock_ai)
    REPLY["content"] = "```json\n" + json.dumps({"vendor": "Sysco Example", "invoice_no": "A-77", "date": "2026-10-20", "lines": [
        {"description": "GROUND BEEF 80/20", "qty": 20, "unit": "lb", "unit_cost": 3.95, "total": 79.0},
        {"description": "Avocados Hass 48ct", "qty": 1, "unit": "case", "unit_cost": None, "total": 52.5},
        {"description": "", "qty": 1}]}) + "\n```"
    up = client.post("/api/invoice/upload", data={"files": [(io.BytesIO(b"\xff\xd8\xff" + b"0" * 50), "inv.jpg")]},
                     content_type="multipart/form-data").json
    name = up["files"][0]["name"]
    r = client.post("/api/ai/invoice", json={"files": [name]})
    assert r.status_code == 200 and r.json["saved"] is False
    inv = r.json["invoice"]
    assert inv["vendor"] == "Sysco Example" and inv["date"] == "2026-10-20" and len(inv["lines"]) == 2
    l0, l1 = inv["lines"]
    assert l0["item_id"] == beef["id"] and l0["unit_cost"] == 3.95
    assert l1["status"] == "new" and l1["unit_cost"] == 52.5  # derived from total / qty
    sent = CALLS[-1]["body"]["messages"][0]["content"]
    assert any(p.get("type") == "image_url" and p["image_url"]["url"].startswith("data:image/jpeg;base64,") for p in sent)
    # nothing saved yet
    assert client.get("/api/items").json["items"][0]["on_hand"] == 0
    # user confirms (edits qty, creates the new product)
    s = client.post("/api/receives/batch", json={"vendor": inv["vendor"], "invoice_no": inv["invoice_no"], "photos": [name], "lines": [
        {"item_id": l0["item_id"], "qty": 18, "unit_cost": l0["unit_cost"]},
        {"new_item": {"name": "Avocados", "unit": "case", "category": "Produce", "zone": "cooler"}, "qty": 1, "unit_cost": 52.5}]})
    assert s.status_code == 201, s.json
    assert all(x["photos"] == [name] for x in s.json["receives"])
    items = {i["name"]: i for i in client.get("/api/items").json["items"]}
    assert items["Ground beef"]["on_hand"] == 18 and items["Ground beef"]["cost"] == 3.95
    assert items["Avocados"]["on_hand"] == 1 and items["Avocados"]["cost"] == 52.5
    assert client.post("/api/receives/batch", json={"photos": ["../x"], "lines": [{"item_id": beef["id"], "qty": 1}]}).status_code == 400


def test_invoice_upload_without_ai_attaches_file(client):
    beef = client.post("/api/items", json={"name": "Beef", "unit": "lb", "par": 1, "category": "P", "zone": "cooler"}).json["item"]
    up = client.post("/api/invoice/upload", data={"files": (io.BytesIO(b"%PDF-1.4"), "inv.pdf")}, content_type="multipart/form-data")
    assert up.status_code == 201
    bad = client.post("/api/invoice/upload", data={"files": (io.BytesIO(b"x"), "a.exe")}, content_type="multipart/form-data")
    assert bad.status_code == 400
    n = up.json["files"][0]["name"]
    s = client.post("/api/receives/batch", json={"photos": [n], "lines": [{"item_id": beef["id"], "qty": 2}]})
    assert s.status_code == 201 and s.json["receives"][0]["photos"] == [n]


def test_clean_invoice_and_items_unit():
    c = ai.clean_invoice({"vendor": " V ", "date": "Oct 5", "lines": [{"description": "Rice", "qty": "2", "unit_cost": "$10.50"},
                                                                     "junk", {"name": "Beans", "total": "8", "qty": 4}]})
    assert c["date"] is None and c["lines"][0]["unit_cost"] == 10.5 and c["lines"][1]["unit_cost"] == 2.0
    items = ai.clean_items({"items": [{"name": "corn tortillas", "qty": 4, "unit": "Pack"}, {"name": "Corn Tortillas"}, {"name": ""},
                                      {"name": "lime", "qty": -3}]})
    assert [i["name"] for i in items] == ["Corn tortillas", "Lime"] and items[0]["unit"] == "pack" and items[1]["qty"] is None
    with pytest.raises(ai.AIError):
        ai.parse_json("no json here")
    with pytest.raises(ai.AIOff):
        ai.propose_shelf({"enabled": False}, "Cooler", [], text="x")


# ---------- shelf proposals ----------

def test_shelf_photo_and_tidy_propose_only(client, mock_ai):
    client.put("/api/sections", json={"sections": ["Lowboy", "Dry shelf 1"]})
    client.post("/api/items", json={"name": "Crema", "unit": "tub", "par": 2, "category": "Dairy", "zone": "lowboy"})
    connect(client, mock_ai)
    REPLY["content"] = json.dumps({"items": [{"name": "Crema", "qty": 3, "unit": "tub", "category": "Dairy"},
                                             {"name": "Queso fresco", "qty": 2, "unit": "ea", "category": "Dairy"}]})
    r = client.post("/api/ai/shelf", data={"section": "lowboy", "text": "", "photo": (io.BytesIO(b"\x89PNG\r\n\x1a\n0"), "shelf.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 200, r.json
    its = r.json["items"]
    assert its[0]["status"] == "matched" and its[1]["status"] == "new" and all(i["zone"] == "lowboy" for i in its)
    assert "Lowboy" in CALLS[-1]["body"]["messages"][0]["content"][0]["text"]
    assert len(client.get("/api/items").json["items"]) == 1  # proposal only — nothing saved
    t = client.post("/api/ai/tidy", json={"section": "dry-shelf-1", "text": "uh corn torts like four packs and rice two bags"})
    assert t.status_code == 200 and all(i["zone"] == "dry-shelf-1" for i in t.json["items"])
    assert client.post("/api/ai/shelf", json={"section": "nope", "text": "x"}).status_code == 400


def test_normalize_unit():
    out, e = sections.normalize(["Cooler", {"key": "cooler", "name": "Walk-in"}], [{"key": "cooler", "name": "Cooler"}])
    assert e is None and out[1]["key"] == "cooler" and out[0]["key"] == "cooler-2"


def test_parenthetical_words_block_false_match():
    from osft import voice, starter_catalog
    m = voice.match_entry("chicken thighs", starter_catalog.CATALOG, None)
    assert m["item"]["name"] == "Chicken thigh boneless"
