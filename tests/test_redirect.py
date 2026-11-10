import json
import time
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import register_errors
from app.routes_redirect import router


class FakeRedis:
    def __init__(self):
        self.kv, self.events = {}, []

    async def get(self, k): return self.kv.get(k)
    async def set(self, k, v, ex=None): self.kv[k] = v
    async def delete(self, k): self.kv.pop(k, None)
    async def incr(self, k):
        self.kv[k] = self.kv.get(k, 0) + 1
        return self.kv[k]
    async def xadd(self, stream, fields, **kw): self.events.append(fields)


class FakePool:
    def __init__(self, row=None): self.row = row
    async def fetchrow(self, *a): return self.row


def make_client(row=None, cached=None):
    app = FastAPI()
    register_errors(app)
    app.include_router(router)
    r = FakeRedis()
    if cached:
        r.kv["link:abc1234"] = json.dumps(cached)
    app.state.redis, app.state.pool = r, FakePool(row)
    app.state.cfg = SimpleNamespace(link_cache_ttl=3600, stream_name="clicks", ip_hash_salt="s")
    app.state.geo = SimpleNamespace(lookup=lambda ip: ("IN", "Pune"))
    return TestClient(app), r


def link(**kw):
    base = {"id": 1, "url": "https://example.com/x?a=1", "status": "active", "exp": None, "limit": None}
    return {**base, **kw}


def test_redirect_is_302_and_logs_click():
    c, r = make_client(cached=link())
    resp = c.get("/abc1234", headers={"user-agent": "Mozilla/5.0", "referer": "https://twitter.com/x"},
                 follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/x?a=1"
    assert r.events[0]["referrer"] == "twitter.com" and r.events[0]["country"] == "IN"
    assert "127.0.0.1" not in json.dumps(r.events)  # raw IP is never emitted


def test_unknown_code_404_and_negative_cached():
    c, r = make_client(row=None)
    assert c.get("/nope123", follow_redirects=False).status_code == 404
    assert r.kv["link:nope123"] == "0"


def test_cache_miss_loads_from_db():
    row = {"id": 5, "original_url": "https://e.com", "status": "active", "expires_at": None, "click_limit": None}
    c, r = make_client(row=row)
    assert c.get("/abc1234", follow_redirects=False).status_code == 302
    assert "link:abc1234" in r.kv


def test_expired_410():
    c, _ = make_client(cached=link(exp=time.time() - 5))
    assert c.get("/abc1234", follow_redirects=False).status_code == 410


def test_disabled_410():
    c, _ = make_client(cached=link(status="disabled"))
    assert c.get("/abc1234", follow_redirects=False).status_code == 410


def test_click_limit_enforced():
    c, _ = make_client(cached=link(limit=2))
    codes = [c.get("/abc1234", follow_redirects=False).status_code for _ in range(3)]
    assert codes == [302, 302, 410]


def test_invalid_code_shape_404():
    c, _ = make_client()
    assert c.get("/favicon.ico", follow_redirects=False).status_code == 404
