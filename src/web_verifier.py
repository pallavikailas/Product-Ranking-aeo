"""DuckDuckGo citation verifier.

Uses the duckduckgo-search package (DDGS) instead of scraping DDG HTML directly,
which is fragile and blocked in many cloud environments.
"""

from __future__ import annotations

import time

from duckduckgo_search import DDGS

_DELAY = 0.5   # seconds between requests to stay within DDG rate limits


def verify_brand(brand: str) -> dict:
    """Return a verification dict for a single brand name."""
    result: dict = {
        "brand": brand,
        "found": False,
        "top_hit_url": None,
        "top_hit_title": None,
    }
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(brand, max_results=1))
        if hits:
            result["found"] = True
            result["top_hit_title"] = hits[0].get("title", "")
            result["top_hit_url"] = hits[0].get("href", "")
    except Exception:
        pass
    return result


def verify_brands(brands: list[str], delay: float = _DELAY) -> list[dict]:
    """Verify multiple brands with a small delay between requests."""
    results: list[dict] = []
    for brand in brands:
        results.append(verify_brand(brand))
        time.sleep(delay)
    return results
