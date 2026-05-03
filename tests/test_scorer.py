"""Offline unit tests for scorer, parser, and models.

These tests use no live API keys — all LLM responses are synthetic fixtures.
Run with: pytest tests/
"""

from __future__ import annotations

import pytest

from src.models import ModelResponse, ScoreCard
from src.parser import parse_products, find_target, score_sentiment
from src.scorer import score_panel


# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_RESPONSE_RANKED_FIRST = """\
1. **Nature Made Magnesium Glycinate** – highly recommended for seniors due to its gentle formula
2. **Doctor's Best High Absorption Magnesium** – excellent bioavailability
3. **Thorne Magnesium Bisglycinate** – premium quality, trusted brand
"""

MOCK_RESPONSE_RANKED_THIRD = """\
1. **Doctor's Best High Absorption Magnesium** – excellent bioavailability
2. **Thorne Magnesium Bisglycinate** – premium option
3. **Nature Made Magnesium Glycinate** – popular choice for seniors
4. **NOW Supplements Magnesium** – budget-friendly
"""

MOCK_RESPONSE_NOT_MENTIONED = """\
1. **Doctor's Best Magnesium** – top pick
2. **Thorne Magnesium** – premium
3. **NOW Supplements Magnesium** – affordable
"""


def _make_response(label: str, text: str, error: str = None) -> ModelResponse:
    return ModelResponse(model_label=label, text=text or "", error=error)


# ── Parser tests ──────────────────────────────────────────────────────────────

def test_parse_products_extracts_ranked_list():
    products = parse_products(MOCK_RESPONSE_RANKED_FIRST)
    assert len(products) == 3
    assert products[0].rank == 1
    assert "Nature Made" in products[0].name
    assert products[1].rank == 2


def test_parse_products_handles_empty():
    assert parse_products("") == []


def test_find_target_ranked():
    products = parse_products(MOCK_RESPONSE_RANKED_FIRST)
    rank, mentioned = find_target(products, MOCK_RESPONSE_RANKED_FIRST, "Nature Made")
    assert rank == 1
    assert mentioned is True


def test_find_target_not_mentioned():
    products = parse_products(MOCK_RESPONSE_NOT_MENTIONED)
    rank, mentioned = find_target(products, MOCK_RESPONSE_NOT_MENTIONED, "Nature Made")
    assert rank is None
    assert mentioned is False


def test_score_sentiment_positive():
    text = "Nature Made is an excellent, highly recommended brand trusted by seniors."
    score = score_sentiment(text, "Nature Made")
    assert score > 0


def test_score_sentiment_absent_brand():
    score = score_sentiment("Some other brand text.", "Nature Made")
    assert score == 0.0


# ── ScoreCard / score_panel tests ─────────────────────────────────────────────

def test_score_panel_perfect_mention():
    responses = [
        _make_response("Model A", MOCK_RESPONSE_RANKED_FIRST),
        _make_response("Model B", MOCK_RESPONSE_RANKED_FIRST),
        _make_response("Model C", MOCK_RESPONSE_RANKED_FIRST),
    ]
    card = score_panel("Nature Made", "best magnesium for seniors", responses, verify_citations=False)
    assert isinstance(card, ScoreCard)
    assert card.mention_rate == 1.0
    assert card.avg_position == 1.0
    assert card.overall > 80  # should be A or better
    assert card.grade in ("A+", "A", "B")


def test_score_panel_zero_mentions():
    responses = [
        _make_response("Model A", MOCK_RESPONSE_NOT_MENTIONED),
        _make_response("Model B", MOCK_RESPONSE_NOT_MENTIONED),
        _make_response("Model C", MOCK_RESPONSE_NOT_MENTIONED),
    ]
    card = score_panel("Nature Made", "best magnesium for seniors", responses, verify_citations=False)
    assert card.mention_rate == 0.0
    assert card.avg_position is None
    assert card.grade == "F"


def test_score_panel_mixed_mentions():
    responses = [
        _make_response("Model A", MOCK_RESPONSE_RANKED_FIRST),
        _make_response("Model B", MOCK_RESPONSE_RANKED_THIRD),
        _make_response("Model C", MOCK_RESPONSE_NOT_MENTIONED),
    ]
    card = score_panel("Nature Made", "best magnesium for seniors", responses, verify_citations=False)
    assert card.mention_rate == pytest.approx(2 / 3, rel=1e-3)
    assert card.avg_position == pytest.approx(2.0)  # (1+3)/2


def test_score_panel_error_response():
    responses = [
        _make_response("Model A", "", error="API timeout"),
        _make_response("Model B", MOCK_RESPONSE_RANKED_FIRST),
    ]
    card = score_panel("Nature Made", "best magnesium for seniors", responses, verify_citations=False)
    assert card.mention_rate == 0.5
    errored = [m for m in card.per_model if m.error]
    assert len(errored) == 1


def test_score_panel_high_score_gets_good_grade():
    responses = [_make_response(f"M{i}", MOCK_RESPONSE_RANKED_FIRST) for i in range(3)]
    card = score_panel("Nature Made", "query", responses, verify_citations=False)
    assert card.grade in ("A+", "A", "B")


def test_scorecard_fields_present():
    responses = [_make_response("M1", MOCK_RESPONSE_RANKED_FIRST)]
    card = score_panel("Nature Made", "test query", responses, verify_citations=False)
    assert hasattr(card, "query")
    assert hasattr(card, "target")
    assert hasattr(card, "overall")
    assert hasattr(card, "grade")
    assert hasattr(card, "mention_rate")
    assert hasattr(card, "avg_position")
    assert hasattr(card, "sentiment_score")
    assert hasattr(card, "citation_score")
    assert hasattr(card, "per_model")
    assert hasattr(card, "verifications")
    assert len(card.per_model) == 1
