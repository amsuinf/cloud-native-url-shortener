"""Unit tests using an in-memory fake store (no Redis needed in CI)."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from src import main


class FakeStore:
    """In-memory Store implementation for fast, hermetic tests."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self.up = True

    def save(self, code: str, url: str, ttl_seconds: int = 0) -> None:
        expiry = time.time() + ttl_seconds if ttl_seconds > 0 else 0
        self._data[code] = (url, expiry)

    def lookup(self, code: str) -> str | None:
        item = self._data.get(code)
        if item is None:
            return None
        url, expiry = item
        if expiry and time.time() > expiry:
            del self._data[code]
            return None
        return url

    def exists(self, code: str) -> bool:
        return self.lookup(code) is not None

    def ping(self) -> bool:
        return self.up


@pytest.fixture
def client(monkeypatch):
    fake = FakeStore()
    monkeypatch.setattr(main, "store", fake)
    return TestClient(main.app), fake


def test_shorten_and_redirect(client):
    c, _ = client
    resp = c.post("/api/shorten", json={"url": "https://example.com/page"})
    assert resp.status_code == 201
    code = resp.json()["code"]

    # Disable redirect following so we can assert on the 307 itself.
    r = c.get(f"/{code}", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "https://example.com/page"


def test_custom_code(client):
    c, _ = client
    resp = c.post(
        "/api/shorten", json={"url": "https://example.com", "custom_code": "mylink"}
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "mylink"


def test_custom_code_conflict(client):
    c, _ = client
    body = {"url": "https://example.com", "custom_code": "dup"}
    assert c.post("/api/shorten", json=body).status_code == 201
    assert c.post("/api/shorten", json=body).status_code == 409


def test_invalid_url_rejected(client):
    c, _ = client
    assert c.post("/api/shorten", json={"url": "not-a-url"}).status_code == 422


def test_unknown_code_404(client):
    c, _ = client
    assert c.get("/nope", follow_redirects=False).status_code == 404


def test_readiness_reflects_redis(client):
    c, fake = client
    assert c.get("/readyz").status_code == 200
    fake.up = False
    assert c.get("/readyz").status_code == 503


def test_liveness_always_ok(client):
    c, _ = client
    assert c.get("/healthz").json() == {"status": "ok"}


def test_metrics_exposed(client):
    c, _ = client
    c.post("/api/shorten", json={"url": "https://example.com"})
    body = c.get("/metrics").text
    assert "links_created_total" in body
