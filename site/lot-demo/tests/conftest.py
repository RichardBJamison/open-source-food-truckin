import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DATA_DIR", tmp_path)
    monkeypatch.setattr(server, "STORE_PATH", tmp_path / "store.json")
    monkeypatch.setattr(server, "PHOTOS_DIR", tmp_path / "photos")
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


@pytest.fixture()
def seeded(client):
    r = client.post("/api/seed", json={})
    assert r.status_code == 200
    return client


SAMPLES = ROOT / "samples"
