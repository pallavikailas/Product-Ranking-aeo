"""Parse AI model responses: extract ranked product lists and brand sentiment."""

from __future__ import annotations

import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .chains import get_llama31_llm
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


class CitationExtraction(BaseModel):
    """Brand/citation extraction with query-aware reasoning."""

    brand_name: Optional[str] = Field(default=None, description="Canonical brand name if present.")
    mentioned: bool = Field(description="Whether the target brand is explicitly or implicitly mentioned.")
    rank: Optional[int] = Field(default=None, description="Product rank for the target brand when present.")
    citations: list[str] = Field(default_factory=list, description="Quoted supporting snippets from response.")
    confidence: float = Field(default=0.0, description="Confidence from 0 to 1.")


def _strip_think(text: str) -> str:
    """Remove <think>…</think> chain-of-thought blocks (Qwen3, DeepSeek-R1)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def parse_products(text: str) -> list[Product]:
    """Extract a numbered product list from raw AI response text."""
    text = _strip_think(text)
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


def extract_brand_context(
    raw: str,
    target_brand: str,
    query: str,
    products: list[Product],
) -> CitationExtraction:
    """Use an LLM extractor so brand matching uses query and contextual cues.

    Falls back to deterministic matching if no LLM is configured.
    """
    llm = get_llama31_llm()
    if llm is None:
        needle = target_brand.lower()
        for p in products:
            if needle in p.name.lower() or needle in p.description.lower():
                return CitationExtraction(
                    brand_name=target_brand,
                    mentioned=True,
                    rank=p.rank,
                    citations=[f"{p.name} — {p.description}"],
                    confidence=0.6,
                )
        if needle in raw.lower():
            return CitationExtraction(brand_name=target_brand, mentioned=True, citations=[target_brand], confidence=0.4)
        return CitationExtraction(brand_name=None, mentioned=False, citations=[], confidence=0.2)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You extract brand evidence from model-generated recommendation lists.
Use semantic matching (aliases, abbreviations, product-level references) with the shopper query context.
Return only structured fields."""),
        ("human", """Target brand: {target_brand}
User query: {query}

Parsed ranked products:
{products_text}

Raw model response:
{raw}

Determine if the target brand appears in the response.
If yes, infer canonical brand name and rank when possible, and return 1-3 short citation snippets from the response.
"""),
    ])
    extractor = prompt | llm.with_structured_output(CitationExtraction)
    products_text = "\n".join(f"{p.rank}. {p.name} — {p.description}" for p in products)
    return extractor.invoke(
        {
            "target_brand": target_brand,
            "query": query,
            "products_text": products_text or "(none)",
            "raw": raw,
        }
    )


def find_target(
    products: list[Product], raw: str, target_brand: str, query: str = ""
) -> tuple[Optional[int], bool]:
    """Return (rank, mentioned) for the target brand using contextual extraction."""
    extraction = extract_brand_context(raw=raw, target_brand=target_brand, query=query, products=products)
    return extraction.rank, extraction.mentioned


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


def process_result(result: ModelResult, target_brand: str, query: str = "") -> ModelResult:
    """Populate parsed fields on a ModelResult in-place and return it."""
    if result.error or not result.raw_response:
        return result
    result.products = parse_products(result.raw_response)
    result.target_rank, result.target_mentioned = find_target(
        result.products, result.raw_response, target_brand, query=query
    )
    result.sentiment_score = score_sentiment(result.raw_response, target_brand)
    return result
