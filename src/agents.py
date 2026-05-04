"""Deep research agent for detailed AEO brand analysis.

A LangGraph ReAct agent that uses web-search tools to investigate why
a brand is performing a certain way in AI answer engines and generates
specific, actionable recommendations.
"""

from __future__ import annotations

import os
from typing import Optional

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from .web_verifier import verify_brand


# ── Tools available to the deep research agent ───────────────────────────────

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


# ── Agent factory ─────────────────────────────────────────────────────────────

def _get_agent_llm():
    """Return the Groq-hosted Llama model for the deep analysis agent."""
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
) -> str:
    """Run a ReAct agent to produce a deep AEO analysis with recommendations.

    Returns a markdown-formatted analysis string.
    """
    llm = _get_agent_llm()
    if llm is None:
        return "Deep analysis unavailable: set GROQ_API_KEY to enable the research agent."

    tools = [search_brand_presence, analyze_aeo_gap]
    agent = create_react_agent(llm, tools)

    rank_desc = f"average rank #{avg_position:.1f}" if avg_position else "not mentioned by any model"
    prompt = (
        f"You are an AEO (Answer Engine Optimization) analyst. "
        f"Investigate the brand '{brand}' for the query: \"{query}\". "
        f"The brand currently has {rank_desc} across AI answer engines.\n\n"
        f"Steps:\n"
        f"1. Use search_brand_presence to verify '{brand}' has a real web presence.\n"
        f"2. Use analyze_aeo_gap with brand='{brand}', query='{query}', "
        f"avg_rank={avg_position if avg_position else -1.0} to generate recommendations.\n"
        f"3. Synthesize findings into a concise, actionable report."
    )

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        messages = result.get("messages", [])
        return messages[-1].content if messages else "Agent returned no output."
    except Exception as exc:
        return f"Deep analysis failed: {exc}"
