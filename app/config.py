import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    base_url: str = "http://localhost:8000"
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_password: str = ""
    code_length: int = 7
    code_multiplier: int = 2654435761
    ip_hash_salt: str = Field(default_factory=lambda: secrets.token_hex(16))
    safe_browsing_api_key: str = ""
    geoip_db_path: str = "/data/GeoLite2-City.mmdb"
    rate_limit_per_min: int = 60
    link_cache_ttl: int = 3600
    stream_name: str = "clicks"


@lru_cache
def get_settings() -> Settings:
    return Settings()
