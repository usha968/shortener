import hashlib
import time

from fastapi import Request

from .errors import ApiError


async def current_user(request: Request) -> int:
    s = request.app.state
    key = request.headers.get("x-api-key")
    if not key:
        raise ApiError(401, "missing_api_key", "Provide your key in the X-API-Key header.")
    key_hash = hashlib.sha256(key.encode()).hexdigest()  # keys are high-entropy, so a fast hash is fine
    user_id = await s.pool.fetchval(
        "SELECT user_id FROM api_keys WHERE key_hash = $1 AND revoked_at IS NULL", key_hash)
    if user_id is None:
        raise ApiError(401, "invalid_api_key", "API key is invalid or revoked.")

    now = int(time.time())
    bucket = f"rl:{user_id}:{now // 60}"
    count = await s.redis.incr(bucket)
    if count == 1:
        await s.redis.expire(bucket, 60)
    if count > s.cfg.rate_limit_per_min:
        raise ApiError(429, "rate_limited", "Too many requests.",
                       headers={"Retry-After": str(60 - now % 60)})
    return user_id
