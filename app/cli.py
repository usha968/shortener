import asyncio
import hashlib
import secrets
import sys

import asyncpg

from .config import get_settings


async def main(email: str) -> None:
    pool = await asyncpg.create_pool(get_settings().database_url)
    uid = await pool.fetchval(
        "INSERT INTO users (email) VALUES ($1) "
        "ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email RETURNING id", email)
    key = "sk_" + secrets.token_urlsafe(32)
    await pool.execute("INSERT INTO api_keys (user_id, key_hash) VALUES ($1, $2)",
                       uid, hashlib.sha256(key.encode()).hexdigest())
    print(f"API key for {email} (shown once): {key}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
