"""Score calculation, grade assignment, and competitor aggregation."""

from __future__ import annotations

from .models import ModelResult


def score_model_result(result: ModelResult) -> float:
    """Score a single model result out of 100.

    Breakdown:
        40 pts — brand was mentioned at all
        40 pts — rank quality  (rank 1 = 40, each step loses 5, rank 9+ = 0)
        20 pts — sentiment     (normalised from -1…+1 to 0…20)
    """
    if result.error:
        return 0.0
    score = 0.0
    if result.target_mentioned:
        score += 40.0
    if result.target_rank is not None:
        score += max(0.0, 40.0 - (result.target_rank - 1) * 5.0)
    score += ((result.sentiment_score + 1) / 2) * 20.0
    return round(score, 2)


def overall_score_and_grade(results: list[ModelResult]) -> tuple[float, str]:
    """Average model scores into a 0-100 overall score and letter grade."""
    valid = [r for r in results if not r.error]
    if not valid:
        return 0.0, "N/A"
    avg = sum(score_model_result(r) for r in valid) / len(valid)
    avg = round(avg, 1)
    grade = (
        "A+" if avg >= 90 else
        "A"  if avg >= 80 else
        "B"  if avg >= 70 else
        "C"  if avg >= 60 else
        "D"  if avg >= 50 else "F"
    )
    return avg, grade


def aggregate_competitors(
    results: list[ModelResult], target_brand: str
) -> dict[str, dict]:
    """Build a cross-model competitor leaderboard.

    Returns a dict keyed by normalised brand slug, sorted by total mentions.
    Each value: {display, mentions, best_rank, sov (share of voice %)}.
    """
    totals: dict[str, dict] = {}
    total_slots = 0
    needle = target_brand.lower()

    for result in results:
        if result.error:
            continue
        for product in result.products:
            total_slots += 1
            name = product.name

            # Determine brand key
            if needle in name.lower():
                brand_key = needle
                display_name = target_brand
            else:
                # Use the first word of the product name as the brand slug
                brand_key = name.split()[0].lower().strip("®™")
                display_name = name

            entry = totals.setdefault(
                brand_key,
                {"display": display_name, "mentions": 0, "best_rank": 999},
            )
            entry["mentions"] += 1
            entry["best_rank"] = min(entry["best_rank"], product.rank)

    # Compute share of voice
    for data in totals.values():
        data["sov"] = (
            round(data["mentions"] / total_slots * 100, 1) if total_slots else 0.0
        )
        if data["best_rank"] == 999:
            data["best_rank"] = None

    return dict(sorted(totals.items(), key=lambda x: -x[1]["mentions"]))
