"""Shared data classes and Pydantic models for the AEO diagnostic pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field


# ── Pydantic models for LangChain structured output ──────────────────────────

class RankedProduct(BaseModel):
    rank: int = Field(description="Position in the ranking list (1 = best)")
    name: str = Field(description="Full brand and product name")
    description: str = Field(description="One sentence describing why it stands out")


class LLMRankingOutput(BaseModel):
    products: list[RankedProduct] = Field(description="Ranked list of products")


# ── New runtime dataclasses ───────────────────────────────────────────────────

@dataclass
class ModelResponse:
    """Raw response from one LLM in the panel."""
    model_label: str
    text: str = ""
    latency_ms: int = 0
    error: Optional[str] = None


@dataclass
class PerModelResult:
    """Parsed and scored result for a single model."""
    model_label: str
    mentioned: bool = False
    position: Optional[int] = None
    sentiment: str = "Neutral"
    competitors: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ScoreCard:
    """Aggregated AEO report card returned by score_panel."""
    query: str
    target: str
    overall: float
    grade: str
    mention_rate: float
    avg_position: Optional[float]
    sentiment_score: float
    citation_score: float
    per_model: list[PerModelResult] = field(default_factory=list)
    verifications: list[dict] = field(default_factory=list)


# ── Legacy dataclasses kept for report.py / scoring.py compatibility ──────────

@dataclass
class Product:
    rank: int
    name: str
    description: str


@dataclass
class ModelResult:
    model_name: str
    raw_response: str = ""
    products: list[Product] = field(default_factory=list)
    target_rank: Optional[int] = None
    target_mentioned: bool = False
    sentiment_score: float = 0.0
    error: Optional[str] = None


@dataclass
class AEOReport:
    query: str
    target_brand: str
    timestamp: str
    results: list[ModelResult] = field(default_factory=list)
    competitors: dict = field(default_factory=dict)
    overall_score: float = 0.0
    grade: str = "N/A"
