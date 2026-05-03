"""DuckDuckGo citation verifier.

Checks whether a brand name returns real search results, helping detect
hallucinated brand citations in LLM responses.
"""

from __future__ import annotations

import time

import requests
from bs4 import BeautifulSoup

_DDG_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AEO-bot/1.0; +https://github.com/aeo-diagnostic)"}
_TIMEOUT = 8


def verify_brand(brand: str) -> dict:
    """Return a verification dict for a single brand name."""
    result: dict = {
        "brand": brand,
        "found": False,
        "top_hit_url": None,
        "top_hit_title": None,
    }
    try:
        resp = requests.post(
            _DDG_URL,
            data={"q": brand, "kl": "us-en"},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        hits = soup.select("a.result__a")
        if hits:
            result["found"] = True
            result["top_hit_title"] = hits[0].get_text(strip=True)
            result["top_hit_url"] = hits[0].get("href", "")
    except Exception:
        pass
    return result


def verify_brands(brands: list[str], delay: float = 0.6) -> list[dict]:
    """Verify multiple brands with a small delay between requests."""
    results: list[dict] = []
    for brand in brands:
        results.append(verify_brand(brand))
        time.sleep(delay)
    return results
