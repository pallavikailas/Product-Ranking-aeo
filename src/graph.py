"""LangGraph state machine orchestrating the full AEO diagnostic pipeline.

Graph shape:
  START
    └─► query_panel       (parallel LangChain calls to all LLMs)
          └─► extract_brands  (pull brand names from responses)
                └─► [verify_citations] ──(conditional on state flag)
                      └─► compute_score
                            └─► END

The graph can be invoked directly via run_aeo_pipeline() for one-shot use,
or composed into larger workflows.
"""

from __future__ import annotations

import time
from typing import Optional

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from .models import ModelResponse, ScoreCard, LLMRankingOutput
from .chains import ALL_LLM_CONFIGS, build_ranking_chain
from .parser import parse_products, find_target, score_sentiment
from .web_verifier import verify_brands


# ── State schema ──────────────────────────────────────────────────────────────

class AEOState(TypedDict):
    query: str
    target_brand: str
    verify_citations: bool
    raw_responses: list[ModelResponse]
    all_brands: list[str]
    verifications: list[dict]
    score_card: Optional[ScoreCard]


# ── Node functions ────────────────────────────────────────────────────────────

def _query_panel(state: AEOState) -> dict:
    """Query every LLM in the panel and collect raw text responses."""
    query = state["query"]
    responses: list[ModelResponse] = []

    for label, get_llm in ALL_LLM_CONFIGS:
        t0 = time.time()
        resp = ModelResponse(model_label=label)
        try:
            llm = get_llm()
            if llm is None:
                resp.error = "API key not configured"
            else:
                chain = build_ranking_chain(llm)
                output: LLMRankingOutput = chain.invoke({"query": query})
                resp.text = "\n".join(
                    f"{p.rank}. **{p.name}** – {p.description}"
                    for p in output.products
                )
        except Exception as exc:
            resp.error = str(exc)
        resp.latency_ms = int((time.time() - t0) * 1000)
        responses.append(resp)

    return {"raw_responses": responses}


def _extract_brands(state: AEOState) -> dict:
    """Extract unique brand names from all LLM responses."""
    brands: set[str] = set()
    for resp in state["raw_responses"]:
        if resp.error or not resp.text:
            continue
        for product in parse_products(resp.text):
            name = product.name.strip("®™ ") if product.name else ""
            if len(name) > 2:
                brands.add(name)
    return {"all_brands": sorted(brands)}


def _verify_citations_node(state: AEOState) -> dict:
    """Hit DuckDuckGo to verify each extracted brand is a real entity."""
    brands = state["all_brands"][:10]  # cap to avoid rate-limiting
    return {"verifications": verify_brands(brands)}


def _compute_score(state: AEOState) -> dict:
    """Score each model result and aggregate into a ScoreCard."""
    from .models import PerModelResult

    target = state["target_brand"]
    per_model: list[PerModelResult] = []
    positions: list[int] = []
    sentiments: list[float] = []
    mention_count = 0

    for resp in state["raw_responses"]:
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
        per_model.append(pm)

    mention_rate = mention_count / max(len(per_model), 1)
    avg_pos = sum(positions) / len(positions) if positions else None
    avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0.0

    verifications = state.get("verifications", [])
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

    card = ScoreCard(
        query=state["query"],
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
    return {"score_card": card}


def _route_verify(state: AEOState) -> str:
    return "verify" if state.get("verify_citations", True) else "score"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_aeo_graph():
    """Construct and compile the LangGraph AEO pipeline."""
    g = StateGraph(AEOState)

    g.add_node("query_panel", _query_panel)
    g.add_node("extract_brands", _extract_brands)
    g.add_node("verify_citations", _verify_citations_node)
    g.add_node("compute_score", _compute_score)

    g.add_edge(START, "query_panel")
    g.add_edge("query_panel", "extract_brands")
    g.add_conditional_edges(
        "extract_brands",
        _route_verify,
        {"verify": "verify_citations", "score": "compute_score"},
    )
    g.add_edge("verify_citations", "compute_score")
    g.add_edge("compute_score", END)

    return g.compile()


def run_aeo_pipeline(
    query: str,
    target_brand: str,
    verify_citations: bool = True,
) -> ScoreCard:
    """Run the full AEO pipeline end-to-end and return a ScoreCard."""
    app = build_aeo_graph()
    final = app.invoke({
        "query": query,
        "target_brand": target_brand,
        "verify_citations": verify_citations,
        "raw_responses": [],
        "all_brands": [],
        "verifications": [],
        "score_card": None,
    })
    return final["score_card"]
