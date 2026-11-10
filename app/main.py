import logging
from contextlib import asynccontextmanager

import asyncpg
import clickhouse_connect
import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import routes_api, routes_redirect
from .config import get_settings
from .errors import register_errors
from .events import GeoLookup
from .safebrowsing import SafeBrowsing

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    s = app.state
    s.cfg = cfg
    s.pool = await asyncpg.create_pool(cfg.database_url, min_size=2, max_size=10)
    s.redis = aioredis.from_url(cfg.redis_url, decode_responses=True)
    s.http = httpx.AsyncClient(timeout=2.0)
    s.safe = SafeBrowsing(s.http, cfg.safe_browsing_api_key)
    s.geo = GeoLookup(cfg.geoip_db_path)
    try:
        s.ch = clickhouse_connect.get_client(
            host=cfg.clickhouse_host,
            port=cfg.clickhouse_port,
            username="default",
            password=cfg.clickhouse_password,
            secure=False,
        )
    except Exception:
        logging.warning("ClickHouse is unavailable; continuing without analytics backend.")
        s.ch = None
    yield
    await s.http.aclose()
    await s.redis.aclose()
    await s.pool.close()


app = FastAPI(title="Shortener", lifespan=lifespan)
register_errors(app)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    s = app.state
    try:
        await s.pool.fetchval("SELECT 1")
        await s.redis.ping()
    except Exception:
        return JSONResponse({"error": "unhealthy", "message": "A dependency is down."}, status_code=503)
    return {"status": "ok"}


app.include_router(routes_api.router)
app.include_router(routes_redirect.router)  # last, so /{code} cannot shadow other routes
