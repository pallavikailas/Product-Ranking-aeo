"""Parse AI model responses: extract ranked product lists and brand sentiment."""

from __future__ import annotations

import re
from typing import Optional

from .models import ModelResult, Product

# ── sentiment word lists ──────────────────────────────────────────────────────
_POSITIVE = {
    "best", "top", "excellent", "great", "highly recommend", "superior",
    "outstanding", "effective", "popular", "trusted", "leading", "premium",
    "ideal", "perfect", "recommended", "quality", "proven", "safe", "favorite",
}
_NEGATIVE = {
    "avoid", "worst", "poor", "bad", "inferior", "not recommended",
    "concerns", "issues", "problems", "disappointing", "overpriced", "unsafe",
}


def parse_products(text: str) -> list[Product]:
    """Extract a numbered product list from raw AI response text."""
    products: list[Product] = []

    # Primary: "1. **Name** – description" (bold optional, dash variants)
    primary = re.compile(
        r"^\s*(\d+)\.\s+\*{0,2}([^*\n\-–—]+?)\*{0,2}"
        r"\s*[-–—]\s*(.+)$",
        re.MULTILINE,
    )
    for m in primary.finditer(text):
        products.append(
            Product(
                rank=int(m.group(1)),
                name=m.group(2).strip(),
                description=m.group(3).strip(),
            )
        )

    if not products:
        # Fallback: plain numbered lines
        for m in re.finditer(r"^\s*(\d+)\.\s+(.+)$", text, re.MULTILINE):
            content = m.group(2).strip().strip("*")
            parts = re.split(r"\s*[-–—:]\s*", content, maxsplit=1)
            products.append(
                Product(
                    rank=int(m.group(1)),
                    name=parts[0].strip(),
                    description=parts[1].strip() if len(parts) > 1 else "",
                )
            )

    return products


def find_target(
    products: list[Product], raw: str, target_brand: str
) -> tuple[Optional[int], bool]:
    """Return (rank, mentioned) for the target brand (case-insensitive)."""
    needle = target_brand.lower()
    for p in products:
        if needle in p.name.lower() or needle in p.description.lower():
            return p.rank, True
    if needle in raw.lower():
        return None, True
    return None, False


def score_sentiment(raw: str, target_brand: str) -> float:
    """Context-aware sentiment for the target brand.  Returns -1 … +1."""
    sentences = re.split(r"[.!\?\n]", raw.lower())
    needle = target_brand.lower()
    relevant = [s for s in sentences if needle in s]
    if not relevant:
        return 0.0
    pos = sum(1 for s in relevant for w in _POSITIVE if w in s)
    neg = sum(1 for s in relevant for w in _NEGATIVE if w in s)
    total = pos + neg
    if total == 0:
        return 0.3  # mentioned but no signal words — assume neutrally positive
    return (pos - neg) / total


def process_result(result: ModelResult, target_brand: str) -> ModelResult:
    """Populate parsed fields on a ModelResult in-place and return it."""
    if result.error or not result.raw_response:
        return result
    result.products = parse_products(result.raw_response)
    result.target_rank, result.target_mentioned = find_target(
        result.products, result.raw_response, target_brand
    )
    result.sentiment_score = score_sentiment(result.raw_response, target_brand)
    return result
