"""LangChain prompt chains for the AEO LLM ranking panel.

Each chain wraps a provider's chat model behind a unified interface:
  {"query": str} → LLMRankingOutput (parsed ranked product list)

Fallback: if Pydantic parsing fails, regex-based parsing is used.
"""

from __future__ import annotations

import os
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableLambda

from .models import LLMRankingOutput, RankedProduct

_RANKING_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """\
A consumer is researching: "{query}"

Please give your top 8–10 recommendations, ranked #1 (best) to #10.
Use this exact format for every entry:

1. **Brand Product Name** – one sentence on why it stands out
2. **Brand Product Name** – one sentence on why it stands out

Be specific with real brand and product names. Do not add extra sections.\
"""),
])


def _text_to_ranking_output(text: str) -> LLMRankingOutput:
    """Parse numbered-list LLM text into a structured LLMRankingOutput."""
    from .parser import parse_products  # avoid circular at module load
    products = parse_products(text)
    return LLMRankingOutput(
        products=[
            RankedProduct(rank=p.rank, name=p.name, description=p.description)
            for p in products
        ]
    )


def build_ranking_chain(llm: BaseChatModel):
    """Return a runnable chain: {"query": str} → LLMRankingOutput."""
    return _RANKING_PROMPT | llm | StrOutputParser() | RunnableLambda(_text_to_ranking_output)


# ── Provider LLM factories ────────────────────────────────────────────────────

def get_openai_llm() -> Optional[BaseChatModel]:
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", temperature=0.3, max_tokens=1200)
    except ImportError:
        return None


def get_anthropic_llm() -> Optional[BaseChatModel]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-6", max_tokens=1200, temperature=0.3)
    except ImportError:
        return None


def get_gemini_llm() -> Optional[BaseChatModel]:
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=os.environ["GEMINI_API_KEY"],
            temperature=0.3,
            max_output_tokens=1200,
        )
    except ImportError:
        return None


# Ordered panel: (display label, LLM factory)
ALL_LLM_CONFIGS: list[tuple[str, callable]] = [
    ("GPT-4o (OpenAI)", get_openai_llm),
    ("Claude Sonnet (Anthropic)", get_anthropic_llm),
    ("Gemini 1.5 Pro (Google)", get_gemini_llm),
]
