"""LangChain prompt chains — all models hosted on Groq for free, fast inference.

<<<<<<< Updated upstream
Panel:
  • Llama 3.3 70B   (Meta)
  • Mixtral 8x7B    (Mistral AI)
  • Gemma 2 9B      (Google)
=======
Panel (all production-tier on Groq):
  • Llama 3.3 70B        (Meta)
  • GPT-OSS 120B         (OpenAI open weights)
  • Llama 4 Scout 17B    (Meta)
  • Llama 3.1 8B Instant (Meta)
  • GPT-OSS 20B          (OpenAI open weights)
  • Qwen3 32B            (Qwen / Alibaba)
>>>>>>> Stashed changes

All three are queried via a single GROQ_API_KEY.
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
    from .parser import parse_products
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


# ── Groq LLM factory ──────────────────────────────────────────────────────────

def _groq_llm(model_name: str) -> Optional[BaseChatModel]:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(model=model_name, temperature=0.3, max_tokens=1200, groq_api_key=key)
    except ImportError:
        return None


def get_llama_llm() -> Optional[BaseChatModel]:
    return _groq_llm("llama-3.3-70b-versatile")


<<<<<<< Updated upstream
def get_mixtral_llm() -> Optional[BaseChatModel]:
    return _groq_llm("mixtral-8x7b-32768")


def get_gemma_llm() -> Optional[BaseChatModel]:
    return _groq_llm("gemma2-9b-it")
=======
def get_llama31_llm() -> Optional[BaseChatModel]:
    return _groq_llm("llama-3.1-8b-instant")


def get_llama4_llm() -> Optional[BaseChatModel]:
    return _groq_llm("meta-llama/llama-4-scout-17b-16e-instruct")


# ── OpenAI open weights ───────────────────────────────────────────────────────

def get_gpt_oss_llm() -> Optional[BaseChatModel]:
    return _groq_llm("openai/gpt-oss-120b")


def get_gpt_oss20_llm() -> Optional[BaseChatModel]:
    return _groq_llm("openai/gpt-oss-20b")


# ── Qwen / Alibaba ────────────────────────────────────────────────────────────

def get_qwen3_llm() -> Optional[BaseChatModel]:
    return _groq_llm("qwen/qwen3-32b")
>>>>>>> Stashed changes


# Ordered panel: (display label, LLM factory)
ALL_LLM_CONFIGS: list[tuple[str, callable]] = [
<<<<<<< Updated upstream
    ("Llama 3.3 70B (Meta / Groq)", get_llama_llm),
    ("Mixtral 8x7B (Mistral / Groq)", get_mixtral_llm),
    ("Gemma 2 9B (Google / Groq)", get_gemma_llm),
=======
    ("Llama 3.3 70B",        get_llama_llm),
    ("GPT-OSS 120B",         get_gpt_oss_llm),
    ("Llama 4 Scout 17B",    get_llama4_llm),
    ("Llama 3.1 8B Instant", get_llama31_llm),
    ("GPT-OSS 20B",          get_gpt_oss20_llm),
    ("Qwen3 32B",            get_qwen3_llm),
>>>>>>> Stashed changes
]
