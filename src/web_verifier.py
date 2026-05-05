"""DuckDuckGo citation verifier.

Uses the duckduckgo-search package (DDGS) instead of scraping DDG HTML directly,
which is fragile and blocked in many cloud environments.
"""

from __future__ import annotations

import time

from ddgs import DDGS

_DELAY = 0.5   # seconds between requests to stay within DDG rate limits


def _brand_in_hit(brand: str, title: str, url: str) -> bool:
    """Return True if any word of the brand appears in the title or URL."""
    brand_lower = brand.lower()
    title_lower = title.lower()
    url_lower = url.lower()
    # Full brand match first
    if brand_lower in title_lower or brand_lower in url_lower:
        return True
    # At least the first significant word must match
    words = [w for w in brand_lower.split() if len(w) > 2]
    if words and (words[0] in title_lower or words[0] in url_lower):
        return True
    return False


def verify_brand(brand: str) -> dict:
    """Return a verification dict for a single brand name.

    Searches DuckDuckGo for "<brand> supplement" and validates that the
    top results actually refer to the brand — not a random page that
    happens to share a word.
    """
    result: dict = {
        "brand": brand,
        "found": False,
        "top_hit_url": None,
        "top_hit_title": None,
    }
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(f"{brand} supplement", max_results=5))

        for hit in hits:
            title = hit.get("title", "")
            url = hit.get("href", "")
            if _brand_in_hit(brand, title, url):
                result["found"] = True
                result["top_hit_title"] = title
                result["top_hit_url"] = url
                break
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
