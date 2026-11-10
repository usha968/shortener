import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit

import geoip2.database
import geoip2.errors
from user_agents import parse as parse_ua

log = logging.getLogger(__name__)
COLUMNS = ["ts", "link_id", "country", "city", "device", "browser", "os", "referrer", "is_bot", "visitor"]


class GeoLookup:
    def __init__(self, path: str):
        try:
            self.reader = geoip2.database.Reader(path)
        except (OSError, ValueError):
            log.warning("GeoIP database not found at %s; countries will be 'XX'", path)
            self.reader = None

    def lookup(self, ip: str) -> tuple[str, str]:
        if not self.reader:
            return "XX", ""
        try:
            r = self.reader.city(ip)
            return r.country.iso_code or "XX", r.city.name or ""
        except (geoip2.errors.AddressNotFoundError, ValueError):
            return "XX", ""


def visitor_hash(ip: str, ua: str, salt: str, day: str) -> str:
    # The salt includes the day, so visitors cannot be linked across days.
    return hashlib.sha256(f"{salt}|{day}|{ip}|{ua}".encode()).hexdigest()[:32]


def referrer_host(ref: str) -> str:
    try:
        return (urlsplit(ref).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def to_row(f: dict) -> list:
    """Stream entry -> ClickHouse row (runs in the worker, so UA parsing stays off the redirect path)."""
    ua = parse_ua(f["ua"])
    device = ("bot" if ua.is_bot else "tablet" if ua.is_tablet else
              "mobile" if ua.is_mobile else "desktop" if ua.is_pc else "other")
    return [datetime.fromtimestamp(float(f["ts"]), tz=timezone.utc), int(f["link_id"]),
            f["country"], f["city"], device, ua.browser.family, ua.os.family,
            f["referrer"], int(ua.is_bot), f["visitor"]]
