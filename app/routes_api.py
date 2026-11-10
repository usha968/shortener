import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field

from .analytics import fetch_stats
from .auth import current_user
from .errors import ApiError
from .links_repo import get_owned, insert_link, serialize
from .validation import ValidationError, validate_slug, validate_url

router = APIRouter(prefix="/api/v1")


class CreateLink(BaseModel):
    url: str
    custom_slug: str | None = None
    expires_at: datetime | None = None
    click_limit: int | None = Field(default=None, gt=0)


class UpdateLink(BaseModel):
    url: str | None = None
    status: Literal["active", "disabled"] | None = None
    expires_at: datetime | None = None
    click_limit: int | None = Field(default=None, gt=0)


def _check_expiry(dt: datetime | None) -> None:
    if dt is None:
        return
    if dt.tzinfo is None:
        raise ApiError(400, "invalid_expiry", "expires_at must include a timezone, e.g. 2026-12-31T23:59:59Z.")
    if dt <= datetime.now(timezone.utc):
        raise ApiError(400, "invalid_expiry", "expires_at must be in the future.")


async def _vetted_url(s, raw: str) -> tuple[str, str]:
    try:
        url = validate_url(raw, urlsplit(s.cfg.base_url).hostname)
    except ValidationError as e:
        raise ApiError(400, e.error, str(e))
    bad = await s.safe.unsafe_urls([url])
    if bad:
        raise ApiError(422, "unsafe_url", "The destination was flagged as malicious or deceptive.")
    return url, ("safe" if bad is not None else "unchecked")


@router.post("/links", status_code=201)
async def create_link(body: CreateLink, request: Request, user_id: int = Depends(current_user)):
    s = request.app.state
    slug = None
    if body.custom_slug:
        try:
            slug = validate_slug(body.custom_slug)
        except ValidationError as e:
            raise ApiError(400, e.error, str(e))
    _check_expiry(body.expires_at)
    url, safety = await _vetted_url(s, body.url)
    row = await insert_link(s, user_id, url, slug, body.expires_at, body.click_limit, safety)
    await s.redis.delete(f"link:{row['code']}")  # clear any cached "not found"
    return serialize(row, s.cfg.base_url)


@router.get("/links")
async def list_links(request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                     user_id: int = Depends(current_user)):
    s = request.app.state
    rows = await s.pool.fetch(
        "SELECT * FROM links WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        user_id, limit, offset)
    return {"items": [serialize(r, s.cfg.base_url) for r in rows], "limit": limit, "offset": offset}


@router.get("/links/{public_id}")
async def get_link(public_id: str, request: Request, user_id: int = Depends(current_user)):
    s = request.app.state
    return serialize(await get_owned(s, public_id, user_id), s.cfg.base_url)


@router.patch("/links/{public_id}")
async def update_link(public_id: str, body: UpdateLink, request: Request, user_id: int = Depends(current_user)):
    s = request.app.state
    row = await get_owned(s, public_id, user_id)
    if row["status"] == "blocked":
        raise ApiError(403, "link_blocked", "This link was blocked and cannot be modified.")
    sent, changes = body.model_fields_set, {}
    if "url" in sent and body.url is not None:
        changes["original_url"], changes["safety"] = await _vetted_url(s, body.url)
    if "status" in sent and body.status is not None:
        changes["status"] = body.status
    if "expires_at" in sent:
        _check_expiry(body.expires_at)
        changes["expires_at"] = body.expires_at
    if "click_limit" in sent:
        changes["click_limit"] = body.click_limit
    if not changes:
        raise ApiError(400, "invalid_request", "No changes supplied.")
    # Column names come from the fixed keys above, never from user input.
    sets = ", ".join(f"{k} = ${i + 3}" for i, k in enumerate(changes))
    row = await s.pool.fetchrow(
        f"UPDATE links SET {sets}, updated_at = now() WHERE public_id = $1 AND user_id = $2 RETURNING *",
        public_id, user_id, *changes.values())
    await s.redis.delete(f"link:{row['code']}")
    return serialize(row, s.cfg.base_url)


@router.delete("/links/{public_id}", status_code=204)
async def disable_link(public_id: str, request: Request, user_id: int = Depends(current_user)):
    s = request.app.state
    row = await get_owned(s, public_id, user_id)
    await s.pool.execute(
        "UPDATE links SET status = 'disabled', updated_at = now() WHERE id = $1 AND status = 'active'", row["id"])
    await s.redis.delete(f"link:{row['code']}")
    return Response(status_code=204)


@router.get("/links/{public_id}/stats")
async def link_stats(public_id: str, request: Request,
                     date_from: date | None = Query(None, alias="from"),
                     date_to: date | None = Query(None, alias="to"),
                     include_bots: bool = False, user_id: int = Depends(current_user)):
    s = request.app.state
    row = await get_owned(s, public_id, user_id)
    d_to = date_to or datetime.now(timezone.utc).date()
    d_from = date_from or d_to - timedelta(days=29)
    if d_from > d_to or (d_to - d_from).days > 366:
        raise ApiError(400, "invalid_range", "'from' must be <= 'to', with a range of at most 366 days.")
    return await asyncio.to_thread(fetch_stats, s.ch, row["id"], d_from, d_to, include_bots)
