import logging

import httpx

log = logging.getLogger(__name__)
URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


class SafeBrowsing:
    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self.client, self.api_key = client, api_key

    async def unsafe_urls(self, urls: list[str]) -> set[str] | None:
        """Returns URLs flagged as unsafe, or None if the check could not run (fail-open)."""
        if not self.api_key or not urls:
            return None
        body = {
            "client": {"clientId": "url-shortener", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE",
                                "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": u} for u in urls[:500]],
            },
        }
        try:
            r = await self.client.post(URL, params={"key": self.api_key}, json=body)
            r.raise_for_status()
        except httpx.HTTPError:
            log.warning("safe browsing unavailable", exc_info=True)
            return None
        return {m["threat"]["url"] for m in r.json().get("matches", [])}
