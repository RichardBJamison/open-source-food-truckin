"""Public demo mode (OSFT_PUBLIC_DEMO=1): locked settings + automatic sample-data restore."""
import json
import time

import pytest

import server
from osft import public_demo as pd


@pytest.fixture()
def demo(seeded, monkeypatch):
    monkeypatch.setattr(pd, "ENABLED", True)
    monkeypatch.setattr(pd, "SNAPSHOT", "")
    return seeded


def test_off_by_default_changes_nothing(seeded):
    assert pd.ENABLED is False
    r = seeded.post("/api/people", json={"name": "A", "login": "a", "role": "admin", "pin": "123456", "pin2": "123456"})
    assert r.status_code != 403 or not r.get_json().get("public_demo")


@pytest.mark.parametrize("method,path,body", [
    ("post", "/api/people", {"name": "A", "login": "a", "role": "admin", "pin": "123456"}),
    ("put", "/api/ai/settings", {"provider": "custom", "base_url": "http://x/v1", "model": "m", "enabled": True}),
    ("put", "/api/settings/ai", {"enabled": True}),
    ("post", "/api/ai/test", {}),
    ("post", "/api/trucks", {"name": "Second"}),
    ("put", "/api/business", {"name": "Hacked"}),
    ("post", "/api/reset", {}),
    ("post", "/api/reset/all", {"confirm": "RESET"}),
    ("post", "/api/restore", {}),
    ("post", "/api/backups", {}),
    ("put", "/api/onboarding", {"phase": "welcome"}),
    ("post", "/api/invoice/upload", {}),
    ("post", "/api/setup/invoices", {}),
    ("post", "/api/receives/abc/photos", {}),
])
def test_locked_in_public_demo(demo, method, path, body):
    r = getattr(demo, method)(path, json=body)
    assert r.status_code == 403 and r.get_json()["public_demo"] is True, path


def test_playing_still_works(demo):
    assert demo.get("/api/dashboard").status_code == 200
    assert demo.get("/api/library/es").get_json()["ok"]
    assert demo.post("/api/library/ask", json={"question": "hola"}).get_json()["mode"] == "off"
    assert demo.put("/api/settings", json={"locale": "es"}).status_code == 200
    item = demo.get("/api/items").get_json()["items"][0]
    assert demo.put(f"/api/items/{item['id']}", json={"par": 7}).status_code == 200
    assert demo.get("/api/ai").status_code == 200


def test_sample_data_restores(demo, tmp_path, monkeypatch):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "store.json").write_text(json.dumps({"marker": "clean"}))
    (snap / "photos").mkdir()
    data = tmp_path / "data"
    data.mkdir()
    (data / "store.json").write_text("{}")
    (data / "junk.txt").write_text("visitor")
    (data / ".session_secret").write_text("keep-me")
    assert pd.restore(data, str(snap))
    assert json.loads((data / "store.json").read_text()) == {"marker": "clean"}
    assert not (data / "junk.txt").exists() and (data / "photos").is_dir()
    assert (data / ".session_secret").read_text() == "keep-me"
    # maybe_restore waits for the interval
    monkeypatch.setattr(pd, "SNAPSHOT", str(snap))
    (data / "junk.txt").write_text("again")
    pd.maybe_restore(data)
    assert (data / "junk.txt").exists()
    pd._last["t"] = time.time() - pd.RESET_SECONDS - 1
    pd.maybe_restore(data)
    assert not (data / "junk.txt").exists()


def test_missing_snapshot_is_harmless(tmp_path):
    assert pd.restore(tmp_path / "data", str(tmp_path / "nope")) is False
