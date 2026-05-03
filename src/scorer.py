"""score_panel: scores pre-fetched LLM responses into a ScoreCard.

Used by app.py and the CLI when responses have already been fetched via
query_all(). For a fully autonomous one-shot run, use graph.run_aeo_pipeline()
instead — it fetches and scores in one LangGraph execution.

Scoring formula (out of 100):
  0.45 × mention_rate × 100       (was brand mentioned at all?)
  0.30 × position_score           (1st→100, 5th→20, absent→0)
  0.15 × sentiment_normalised     (−1…+1 mapped to 0…100)
  0.10 × citation_score           (% of cited brands found on the web)
"""

from __future__ import annotations

from .models import ModelResponse, PerModelResult, ScoreCard
from .parser import parse_products, find_target, score_sentiment
from .web_verifier import verify_brands


def score_panel(
    target: str,
    query: str,
    responses: list[ModelResponse],
    verify_citations: bool = True,
) -> ScoreCard:
    """Score a list of LLM responses and return an aggregated ScoreCard."""
    per_model: list[PerModelResult] = []
    positions: list[int] = []
    sentiments: list[float] = []
    mention_count = 0
    all_brands: set[str] = set()

    for resp in responses:
        pm = PerModelResult(model_label=resp.model_label, error=resp.error)
        if not resp.error and resp.text:
            products = parse_products(resp.text)
            rank, mentioned = find_target(products, resp.text, target)
            sent = score_sentiment(resp.text, target)

            pm.mentioned = mentioned
            pm.position = rank
            pm.sentiment = "Positive" if sent > 0.2 else "Negative" if sent < -0.2 else "Neutral"
            pm.competitors = [
                p.name for p in products if target.lower() not in p.name.lower()
            ][:5]

            if mentioned:
                mention_count += 1
            if rank:
                positions.append(rank)
            sentiments.append(sent)

            for p in products:
                name = p.name.strip("®™ ") if p.name else ""
                if len(name) > 2:
                    all_brands.add(name)

        per_model.append(pm)

    mention_rate = mention_count / max(len(per_model), 1)
    avg_pos = sum(positions) / len(positions) if positions else None
    avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0.0

    # Citation verification via DuckDuckGo
    verifications: list[dict] = []
    if verify_citations and all_brands:
        verifications = verify_brands(sorted(all_brands)[:10])

    citation_score = (
        sum(1 for v in verifications if v["found"]) / len(verifications) * 100
        if verifications else 100.0
    )

    position_score = max(0.0, 100.0 - (avg_pos - 1) * 20.0) if avg_pos else 0.0

    overall = round(
        0.45 * mention_rate * 100
        + 0.30 * position_score
        + 0.15 * ((avg_sent + 1) / 2 * 100)
        + 0.10 * citation_score,
        1,
    )

    grade = (
        "A+" if overall >= 90 else
        "A"  if overall >= 80 else
        "B"  if overall >= 70 else
        "C"  if overall >= 55 else
        "D"  if overall >= 40 else "F"
    )

    return ScoreCard(
        query=query,
        target=target,
        overall=overall,
        grade=grade,
        mention_rate=mention_rate,
        avg_position=avg_pos,
        sentiment_score=round(avg_sent * 100, 1),
        citation_score=round(citation_score, 1),
        per_model=per_model,
        verifications=verifications,
    )
