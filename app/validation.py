import ipaddress
import re
from urllib.parse import urlsplit

RESERVED = {
    "api", "admin", "login", "logout", "signup", "register", "dashboard", "static",
    "assets", "docs", "openapi", "healthz", "health", "status", "www", "app",
    "settings", "account", "billing", "help", "support", "about", "terms", "privacy",
    "favicon", "robots", "sitemap",
}
SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
MAX_URL_LEN = 2048


class ValidationError(ValueError):
    def __init__(self, error: str, message: str):
        super().__init__(message)
        self.error = error


def validate_url(raw: str, own_host: str | None = None) -> str:
    url = raw.strip()
    if not url or len(url) > MAX_URL_LEN or re.search(r"[\s\x00-\x1f]", url):
        raise ValidationError("invalid_url", "URL is empty, too long, or contains whitespace.")
    try:
        parts = urlsplit(url)
        _ = parts.port  # raises ValueError on a malformed port
    except ValueError:
        raise ValidationError("invalid_url", "URL is malformed.")
    if parts.scheme.lower() not in ("http", "https"):
        raise ValidationError("invalid_url", "Only http and https URLs are allowed.")
    host = (parts.hostname or "").lower()
    if not host:
        raise ValidationError("invalid_url", "URL must include a host.")
    if parts.username or parts.password:
        raise ValidationError("invalid_url", "URLs with embedded credentials are not allowed.")
    if host == "localhost" or host.endswith((".local", ".internal")) or host == own_host:
        raise ValidationError("invalid_url", "This host is not allowed.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise ValidationError("invalid_url", "Private or reserved IP addresses are not allowed.")
    return url


def validate_slug(slug: str) -> str:
    if not SLUG_RE.match(slug):
        raise ValidationError("invalid_slug", "Slug must be 3-32 characters: letters, digits, '-' or '_'.")
    if slug.lower() in RESERVED:
        raise ValidationError("reserved_slug", "This slug is reserved.")
    return slug
