"""Shared data classes for the AEO diagnostic pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


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
    sentiment_score: float = 0.0  # -1 … +1
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
