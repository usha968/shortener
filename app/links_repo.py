import secrets

import asyncpg

from .codegen import make_code
from .errors import ApiError


def serialize(row, base_url: str) -> dict:
    return {
        "id": row["public_id"],
        "short_url": f"{base_url.rstrip('/')}/{row['code']}",
        "original_url": row["original_url"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat().replace("+00:00", "Z"),
        "expires_at": row["expires_at"].isoformat().replace("+00:00", "Z") if row["expires_at"] else None,
        "click_limit": row["click_limit"],
    }


_INSERT = """
INSERT INTO links (id, public_id, code, user_id, original_url, is_custom, expires_at, click_limit,
                   safety, last_scanned_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CASE WHEN $9 = 'safe' THEN now() END)
RETURNING *"""


async def insert_link(s, user_id, url, slug, expires_at, click_limit, safety):
    public_id = "lnk_" + secrets.token_hex(6)
    if slug:
        link_id = await s.pool.fetchval("SELECT nextval('link_id_seq')")
        try:
            return await s.pool.fetchrow(_INSERT, link_id, public_id, slug, user_id, url, True,
                                         expires_at, click_limit, safety)
        except asyncpg.UniqueViolationError:
            raise ApiError(409, "slug_taken", "That slug is already in use.")
    # The loop only repeats if a generated code equals an existing custom slug.
    for _ in range(5):
        link_id = await s.pool.fetchval("SELECT nextval('link_id_seq')")
        code = make_code(link_id, s.cfg.code_multiplier, s.cfg.code_length)
        try:
            return await s.pool.fetchrow(_INSERT, link_id, public_id, code, user_id, url, False,
                                         expires_at, click_limit, safety)
        except asyncpg.UniqueViolationError:
            continue
    raise ApiError(503, "code_generation_failed", "Could not allocate a short code. Retry.")


async def get_owned(s, public_id: str, user_id: int):
    row = await s.pool.fetchrow("SELECT * FROM links WHERE public_id = $1 AND user_id = $2",
                                public_id, user_id)
    if row is None:
        raise ApiError(404, "not_found", "Link not found.")
    return row
