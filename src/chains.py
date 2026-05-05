"""LangChain prompt chains — all models hosted on Groq for free, fast inference.

Panel:
  • Llama 3.3 70B          (Meta)
  • GPT-OSS 120B           (OpenAI)
  • Mistral Saba 24B       (Mistral)
  • GPT-OSS 20B            (OpenAI)
  • Qwen3 32B              (Alibaba)
  • DeepSeek R1 Distill    (DeepSeek)

All six are queried via a single GROQ_API_KEY.
"""

from __future__ import annotations

import os
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models import BaseChatModel

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


def build_ranking_chain(llm: BaseChatModel):
    """Return a runnable chain: {"query": str} → raw response text string."""
    return _RANKING_PROMPT | llm | StrOutputParser()


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


# ── Meta ──────────────────────────────────────────────────────────────────────

def get_llama_llm() -> Optional[BaseChatModel]:
    return _groq_llm("llama-3.3-70b-versatile")


def get_gpt_oss_llm() -> Optional[BaseChatModel]:
    return _groq_llm("openai/gpt-oss-120b")


def get_mistral_llm() -> Optional[BaseChatModel]:
    return _groq_llm("mistral-saba-24b")


def get_gpt_oss20_llm() -> Optional[BaseChatModel]:
    return _groq_llm("openai/gpt-oss-20b")


def get_qwen3_llm() -> Optional[BaseChatModel]:
    return _groq_llm("qwen/qwen3-32b")


def get_deepseek_llm() -> Optional[BaseChatModel]:
    return _groq_llm("deepseek-r1-distill-llama-70b")


# Ordered panel: (display label, LLM factory)
ALL_LLM_CONFIGS: list[tuple[str, callable]] = [
    ("Llama 3.3 70B",       get_llama_llm),
    ("GPT-OSS 120B",        get_gpt_oss_llm),
    ("Mistral Saba 24B",    get_mistral_llm),
    ("GPT-OSS 20B",         get_gpt_oss20_llm),
    ("Qwen3 32B",           get_qwen3_llm),
    ("DeepSeek R1 Distill", get_deepseek_llm),
]
