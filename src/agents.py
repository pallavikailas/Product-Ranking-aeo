"""Deep research agent for detailed AEO brand analysis.

A LangGraph ReAct agent that uses web-search tools to investigate why
a brand is performing a certain way in AI answer engines and generates
specific, actionable recommendations — including temporal analysis based
on each model's knowledge cutoff date.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from .web_verifier import verify_brand

# ── Model info: cutoff dates ──────────────────────────────────────────────────

MODEL_INFO: dict[str, dict] = {
    "Llama 3.3 70B":        {"cutoff": "December 2023",  "web_search": False},
    "GPT-OSS 120B":         {"cutoff": "March 2024",     "web_search": False},
    "Llama 4 Scout 17B":    {"cutoff": "March 2025",     "web_search": False},
    "Compound":             {"cutoff": "real-time",      "web_search": True},
    "Qwen3 32B":            {"cutoff": "September 2024", "web_search": False},
    "Llama 3.1 8B Instant": {"cutoff": "December 2023",  "web_search": False},
}

# Models with significantly more recent knowledge than Dec-2023 baseline
_NEWER_CUTOFFS = {"Llama 4 Scout 17B", "Qwen3 32B"}


def _months_ago(cutoff_str: str) -> str:
    try:
        cutoff = datetime.strptime(cutoff_str, "%B %Y")
        months = max(1, round((datetime.now() - cutoff).days / 30))
        return f"~{months} months ago"
    except Exception:
        return "unknown"


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def search_brand_presence(brand: str) -> str:
    """Search the web to verify a brand's online presence.

    Returns a summary of whether the brand was found and what the top result is.
    """
    result = verify_brand(brand)
    if result["found"]:
        return (
            f"'{brand}' is verified online.\n"
            f"  Top result: {result['top_hit_title']}\n"
            f"  URL: {result['top_hit_url']}"
        )
    return f"'{brand}' could NOT be verified — possible AI hallucination or very low web presence."


@tool
def analyze_aeo_gap(brand: str, query: str, avg_rank: float = -1.0) -> str:
    """Analyze why a brand is underperforming in AEO and suggest targeted fixes.

    Args:
        brand: The target brand name.
        query: The original shopper query.
        avg_rank: Average rank across models (-1 means not mentioned).
    """
    lines = [f"AEO Gap Analysis — '{brand}' for query: \"{query}\"", ""]

    if avg_rank < 0:
        lines += [
            "Status: Brand was NOT mentioned by any LLM.",
            "",
            "Root causes:",
            "  • Insufficient authoritative web presence for this query",
            "  • Missing structured data (JSON-LD product/organization schema)",
            "  • No third-party editorial coverage on review sites",
            "",
            "Recommended actions:",
            "  1. Create a dedicated FAQ page targeting this exact query",
            "  2. Add JSON-LD Product schema with key attributes (ingredients, certifications)",
            "  3. Earn reviews on authoritative sites (Consumer Reports, Healthline, Wirecutter)",
            "  4. Publish comparison content vs. top-ranking competitors",
        ]
    elif avg_rank > 3:
        lines += [
            f"Status: Brand ranks #{avg_rank:.1f} on average — outside the top-3 recommendation zone.",
            "",
            "Root causes:",
            "  • Competitors have stronger editorial link profiles",
            "  • Product description lacks semantic keywords matching consumer intent",
            "  • Fewer third-party endorsements than top-ranked brands",
            "",
            "Recommended actions:",
            "  1. Build comparison-style content (e.g. 'Brand X vs. Competitor Y')",
            "  2. Earn backlinks from category-specific health/supplement authorities",
            "  3. Add consumer-intent phrases to product copy (e.g. 'for seniors', 'doctor-recommended')",
            "  4. Increase review velocity on Amazon, Trustpilot, and Google",
        ]
    else:
        lines += [
            f"Status: Brand ranks #{avg_rank:.1f} — strong top-3 visibility.",
            "",
            "Recommended actions to maintain position:",
            "  1. Refresh product pages quarterly to signal content freshness",
            "  2. Monitor emerging competitors entering this query space",
            "  3. Maintain review velocity to sustain authority signals",
        ]

    return "\n".join(lines)


@tool
def analyze_temporal_context(brand: str, mentioned_by: str, not_mentioned_by: str) -> str:
    """Analyse how knowledge-cutoff dates affect which models mention a brand.

    Divergence between older and newer cutoff models reveals AEO trajectory.

    Args:
        brand: The target brand.
        mentioned_by: Comma-separated list of models that DID mention the brand.
        not_mentioned_by: Comma-separated list of models that did NOT mention it.
    """
    now_str = datetime.now().strftime("%B %Y")
    lines = [
        f"Temporal Analysis — '{brand}' (as of {now_str})",
        "",
        "Panel model details:",
    ]

    mentioned_list     = [m.strip() for m in mentioned_by.split(",")     if m.strip() and m.strip() != "none"]
    not_mentioned_list = [m.strip() for m in not_mentioned_by.split(",") if m.strip() and m.strip() != "none"]

    for model in mentioned_list + not_mentioned_list:
        info = MODEL_INFO.get(model, {"cutoff": "unknown", "web_search": False})
        ws   = info.get("web_search", False)
        cut  = info["cutoff"]
        mark = "✅" if model in mentioned_list else "❌"
        tag  = "🌐 live web search" if ws else f"📚 trained {cut} ({_months_ago(cut)})"
        lines.append(f"  {mark} {model}  [{tag}]")

    training_mentioned     = [m for m in mentioned_list     if not MODEL_INFO.get(m, {}).get("web_search")]
    training_not_mentioned = [m for m in not_mentioned_list if not MODEL_INFO.get(m, {}).get("web_search")]
    search_mentioned       = [m for m in mentioned_list     if MODEL_INFO.get(m, {}).get("web_search")]
    search_not_mentioned   = [m for m in not_mentioned_list if MODEL_INFO.get(m, {}).get("web_search")]

    newer_mention = any(m in _NEWER_CUTOFFS for m in training_mentioned)
    newer_miss    = any(m in _NEWER_CUTOFFS for m in training_not_mentioned)
    older_mention = any(m not in _NEWER_CUTOFFS for m in training_mentioned)
    older_miss    = any(m not in _NEWER_CUTOFFS for m in training_not_mentioned)

    lines += ["", "── Temporal interpretation ─────────────────────────────────────"]

    if not training_mentioned and not training_not_mentioned:
        lines.append("  No training-data models in this comparison.")
    elif newer_mention and older_miss:
        lines.append(
            "  → Newer-cutoff models mention the brand; older ones don't.\n"
            "    Your AEO/SEO work from the past 12–24 months is paying off.\n"
            "    Older models will reflect this at their next training cycle."
        )
    elif older_mention and newer_miss:
        lines.append(
            "  → Older-cutoff models mention the brand; newer ones don't.\n"
            "    The brand may have lost authority recently — investigate\n"
            "    negative press, product changes, or rising competitors."
        )
    elif not training_mentioned:
        lines.append(
            "  → No model mentions the brand.\n"
            "    This is a structural issue (low web authority).\n"
            "    A comprehensive AEO/SEO overhaul is required."
        )
    else:
        lines.append(
            "  → Visibility is consistent across model generations.\n"
            "    Brand authority is stable. Focus on pushing into the top-3 positions."
        )

    if search_mentioned or search_not_mentioned:
        lines += ["", "── Live web-search models ──────────────────────────────────────"]
        if search_mentioned:
            lines.append(
                f"  ✅ {', '.join(search_mentioned)} found the brand via live search.\n"
                "    Current web presence is strong for this query."
            )
        if search_not_mentioned:
            lines.append(
                f"  ❌ {', '.join(search_not_mentioned)} could NOT find the brand via live search.\n"
                "    Fix: improve on-page SEO, structured data, and review velocity.\n"
                "    For web-search models, training cutoff is irrelevant — only live signals count."
            )

    return "\n".join(lines)


# ── Agent factory ─────────────────────────────────────────────────────────────

def _get_agent_llm():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, max_tokens=1024, groq_api_key=key)
    except ImportError:
        return None


def run_deep_analysis(
    brand: str,
    query: str,
    avg_position: Optional[float] = None,
    per_model: Optional[list] = None,
) -> str:
    """Run a ReAct agent to produce a deep AEO analysis with temporal insights.

    Returns a markdown-formatted analysis string.
    """
    llm = _get_agent_llm()
    if llm is None:
        return "Deep analysis unavailable: set GROQ_API_KEY to enable the research agent."

    mentioned_models:     list[str] = []
    not_mentioned_models: list[str] = []
    if per_model:
        for pm in per_model:
            if isinstance(pm, dict):
                label, mentioned = pm.get("model_label", ""), pm.get("mentioned", False)
            else:
                label, mentioned = getattr(pm, "model_label", ""), getattr(pm, "mentioned", False)
            (mentioned_models if mentioned else not_mentioned_models).append(label)

    mentioned_str     = ", ".join(mentioned_models)     or "none"
    not_mentioned_str = ", ".join(not_mentioned_models) or "none"

    tools = [search_brand_presence, analyze_aeo_gap, analyze_temporal_context]
    agent = create_react_agent(llm, tools)

    rank_desc = f"average rank #{avg_position:.1f}" if avg_position else "not mentioned by any model"
    prompt = (
        f"You are an AEO (Answer Engine Optimization) analyst.\n"
        f"Investigate the brand '{brand}' for the query: \"{query}\". "
        f"The brand currently has {rank_desc} across AI answer engines.\n\n"
        f"Models that DID mention the brand: {mentioned_str}\n"
        f"Models that did NOT mention the brand: {not_mentioned_str}\n\n"
        f"Steps:\n"
        f"1. Use search_brand_presence to verify '{brand}' has a real web presence.\n"
        f"2. Use analyze_temporal_context with brand='{brand}', "
        f"mentioned_by='{mentioned_str}', not_mentioned_by='{not_mentioned_str}' "
        f"to interpret what training cutoffs reveal.\n"
        f"3. Use analyze_aeo_gap with brand='{brand}', query='{query}', "
        f"avg_rank={avg_position if avg_position else -1.0} to generate recommendations.\n"
        f"4. Synthesize all findings into a concise, actionable report with clear sections."
    )

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        messages = result.get("messages", [])
        return messages[-1].content if messages else "Agent returned no output."
    except Exception as exc:
        return f"Deep analysis failed: {exc}"
