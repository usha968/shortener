import asyncio
import logging

import asyncpg
import httpx
import redis.asyncio as aioredis

from app.config import get_settings
from app.safebrowsing import SafeBrowsing

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rescan")
INTERVAL_S = 3600
STALE = "7 days"


async def scan_once(pool, redis, safe) -> int:
    blocked = 0
    while True:
        rows = await pool.fetch(
            "SELECT id, code, original_url FROM links WHERE status = 'active' AND "
            "(last_scanned_at IS NULL OR last_scanned_at < now() - $1::interval) "
            "ORDER BY last_scanned_at NULLS FIRST LIMIT 500", STALE)
        if not rows:
            return blocked
        bad = await safe.unsafe_urls([r["original_url"] for r in rows])
        if bad is None:  # API unavailable: try again next cycle
            return blocked
        for r in rows:
            if r["original_url"] in bad:
                await pool.execute("UPDATE links SET status='blocked', safety='unsafe', "
                                   "last_scanned_at=now(), updated_at=now() WHERE id=$1", r["id"])
                await redis.delete(f"link:{r['code']}")
                blocked += 1
            else:
                await pool.execute("UPDATE links SET safety='safe', last_scanned_at=now() WHERE id=$1", r["id"])


async def main() -> None:
    cfg = get_settings()
    pool = await asyncpg.create_pool(cfg.database_url, min_size=1, max_size=2)
    redis = aioredis.from_url(cfg.redis_url, decode_responses=True)
    async with httpx.AsyncClient(timeout=5.0) as http:
        safe = SafeBrowsing(http, cfg.safe_browsing_api_key)
        while True:
            try:
                log.info("rescan blocked %d links", await scan_once(pool, redis, safe))
            except Exception:
                log.exception("rescan failed")
            await asyncio.sleep(INTERVAL_S)


if __name__ == "__main__":
    asyncio.run(main())
