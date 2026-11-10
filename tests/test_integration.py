import os
import time

import httpx
import pytest

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
KEY = os.environ.get("TEST_API_KEY")
pytestmark = pytest.mark.skipif(not KEY, reason="set TEST_API_KEY (see app.cli) and run the stack")


def test_create_redirect_and_stats():
    h = {"X-API-Key": KEY}
    with httpx.Client(base_url=BASE, headers=h, follow_redirects=False) as c:
        bad = c.post("/api/v1/links", json={"url": "javascript:alert(1)"})
        assert bad.status_code == 400 and bad.json()["error"] == "invalid_url"

        created = c.post("/api/v1/links", json={"url": "https://example.com/products?utm_source=email"})
        assert created.status_code == 201
        link = created.json()
        code = link["short_url"].rsplit("/", 1)[1]
        assert len(code) == 7

        r = c.get(f"/{code}", headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"})
        assert r.status_code == 302
        assert r.headers["location"] == "https://example.com/products?utm_source=email"

        for _ in range(20):  # analytics is asynchronous, so poll
            stats = c.get(f"/api/v1/links/{link['id']}/stats").json()
            if stats["total_clicks"] >= 1:
                break
            time.sleep(1)
        assert stats["total_clicks"] >= 1
        assert stats["devices"].get("mobile", 0) >= 1
