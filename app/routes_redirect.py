import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from .errors import ApiError
from .events import referrer_host, visitor_hash
from .validation import SLUG_RE

log = logging.getLogger(__name__)
router = APIRouter()


async def _load(s, code: str) -> dict | None:
    key = f"link:{code}"
    raw = await s.redis.get(key)
    if raw is not None:
        return None if raw == "0" else json.loads(raw)
    row = await s.pool.fetchrow(
        "SELECT id, original_url, status, expires_at, click_limit FROM links WHERE code = $1", code)
    if row is None:
        await s.redis.set(key, "0", ex=60)  # short negative cache against scans
        return None
    exp = row["expires_at"].timestamp() if row["expires_at"] else None
    link = {"id": row["id"], "url": row["original_url"], "status": row["status"],
            "exp": exp, "limit": row["click_limit"]}
    ttl = s.cfg.link_cache_ttl
    if exp:
        ttl = max(1, min(ttl, int(exp - time.time())))
    await s.redis.set(key, json.dumps(link), ex=ttl)
    return link


async def track_click(app, link_id: int, ip: str, ua: str, referer: str) -> None:
    """Runs after the response is sent. Failures are logged and never reach the user."""
    s = app.state
    try:
        country, city = s.geo.lookup(ip)
        now = datetime.now(timezone.utc)
        await s.redis.xadd(s.cfg.stream_name, {
            "ts": f"{now.timestamp():.3f}", "link_id": link_id, "country": country, "city": city,
            "ua": ua[:512], "referrer": referrer_host(referer),
            "visitor": visitor_hash(ip, ua, s.cfg.ip_hash_salt, now.date().isoformat()),
        }, maxlen=1_000_000, approximate=True)  # raw IP never leaves this function
    except Exception:
        log.exception("failed to record click for link %s", link_id)


@router.get("/{code}", include_in_schema=False)
async def redirect(code: str, request: Request, bg: BackgroundTasks):
    s = request.app.state
    if not SLUG_RE.match(code):
        raise ApiError(404, "not_found", "Link not found.")
    link = await _load(s, code)
    if link is None:
        raise ApiError(404, "not_found", "Link not found.")
    if link["status"] != "active":
        raise ApiError(410, "link_unavailable", "This link has been disabled.")
    if link["exp"] and link["exp"] <= time.time():
        raise ApiError(410, "link_expired", "This link has expired.")
    if link["limit"]:
        if await s.redis.incr(f"clicks:{code}") > link["limit"]:
            raise ApiError(410, "click_limit_reached", "This link has reached its click limit.")
    bg.add_task(track_click, request.app, link["id"],
                request.client.host if request.client else "0.0.0.0",
                request.headers.get("user-agent", ""), request.headers.get("referer", ""))
    return RedirectResponse(link["url"], status_code=302, headers={"Cache-Control": "no-store"})
