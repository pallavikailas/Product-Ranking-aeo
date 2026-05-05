"""
DuckDuckGo citation verifier (Hybrid: rule-based + agentic via Groq)

- Fast path: deterministic string matching
- Fallback: LLM-based semantic verification using Groq
"""

from __future__ import annotations

import time
import os
import json
from typing import List, Dict

from ddgs import DDGS
from groq import Groq

_DELAY = 0.5  # seconds between requests
GROQ_MODEL = "llama3-70b-8192"  # fast + strong reasoning

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -------------------------------
# Rule-based verification (FAST)
# -------------------------------
def _brand_in_hit(brand: str, title: str, url: str) -> bool:
    brand_lower = brand.lower()
    title_lower = title.lower()
    url_lower = url.lower()

    # Full match
    if brand_lower in title_lower or brand_lower in url_lower:
        return True

    # First significant word match
    words = [w for w in brand_lower.split() if len(w) > 2]
    if words and (words[0] in title_lower or words[0] in url_lower):
        return True

    return False


# -------------------------------
# Agentic verification (Groq LLM)
# -------------------------------
def agent_verify_brand(brand: str, title: str, url: str) -> Dict:
    prompt = f"""
                    You are verifying whether a search result refers to a specific brand.
                    Brand: {brand}
                    Title: {title}
                    URL: {url}
                    Return JSON:
                    {{
                        "refers_to_brand": true/false,
                        "confidence": number between 0 and 1
                    }}
                    """
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()

        # Safe JSON parsing
        parsed = json.loads(content)
        return parsed

    except Exception:
        return {"refers_to_brand": False, "confidence": 0.0}


# -------------------------------
# Main verification logic
# -------------------------------
def verify_brand(brand: str) -> Dict:
    result: Dict = {
        "brand": brand,
        "found": False,
        "top_hit_url": None,
        "top_hit_title": None,
        "method": None,  # "rule" or "agent"
        "confidence": 0.0,
    }

    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(f"{brand} supplement", max_results=5))

        for hit in hits:
            title = hit.get("title", "")
            url = hit.get("href", "")

            # -----------------------
            # Step 1: Rule-based
            # -----------------------
            if _brand_in_hit(brand, title, url):
                result.update({
                    "found": True,
                    "top_hit_title": title,
                    "top_hit_url": url,
                    "method": "rule",
                    "confidence": 1.0
                })
                break

            # -----------------------
            # Step 2: Agent fallback
            # -----------------------
            agent_result = agent_verify_brand(brand, title, url)

            if (
                agent_result.get("refers_to_brand")
                and agent_result.get("confidence", 0) > 0.7
            ):
                result.update({
                    "found": True,
                    "top_hit_title": title,
                    "top_hit_url": url,
                    "method": "agent",
                    "confidence": agent_result.get("confidence", 0),
                })
                break

    except Exception:
        pass

    return result


# -------------------------------
# Batch processing
# -------------------------------
def verify_brands(brands: List[str], delay: float = _DELAY) -> List[Dict]:
    results: List[Dict] = []

    for brand in brands:
        results.append(verify_brand(brand))
        time.sleep(delay)

    return results
