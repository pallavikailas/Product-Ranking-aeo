"""LangChain prompt chains — all models hosted on Groq for free, fast inference.

Panel (all production-tier on Groq):
  • Llama 3.3 70B        (Meta)
  • GPT-OSS 120B         (OpenAI open weights)
  • Llama 4 Scout 17B    (Meta)
  • Gemma 2 9B           (Google)
  • DeepSeek R1 70B      (DeepSeek)
  • QwQ 32B              (Qwen / Alibaba)

All six are queried via a single GROQ_API_KEY.
The chain returns the raw LLM text so the regex parser in scorer.py
handles all response format variations without losing data.

Note: Anthropic Claude is not available on Groq (requires Anthropic API).
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


def get_llama4_llm() -> Optional[BaseChatModel]:
    return _groq_llm("meta-llama/llama-4-scout-17b-16e-instruct")


# ── OpenAI open weights ───────────────────────────────────────────────────────

def get_gpt_oss_llm() -> Optional[BaseChatModel]:
    return _groq_llm("openai/gpt-oss-120b")


# ── Google ────────────────────────────────────────────────────────────────────

def get_gemma_llm() -> Optional[BaseChatModel]:
    return _groq_llm("gemma2-9b-it")


# ── DeepSeek ──────────────────────────────────────────────────────────────────

def get_deepseek_llm() -> Optional[BaseChatModel]:
    return _groq_llm("deepseek-r1-distill-llama-70b")


# ── Qwen / Alibaba ────────────────────────────────────────────────────────────

def get_qwq_llm() -> Optional[BaseChatModel]:
    return _groq_llm("qwen-qwq-32b")


# Ordered panel: (display label, LLM factory)
ALL_LLM_CONFIGS: list[tuple[str, callable]] = [
    ("Llama 3.3 70B (Meta / Groq)",          get_llama_llm),
    ("GPT-OSS 120B (OpenAI / Groq)",          get_gpt_oss_llm),
    ("Llama 4 Scout 17B (Meta / Groq)",       get_llama4_llm),
    ("Gemma 2 9B (Google / Groq)",            get_gemma_llm),
    ("DeepSeek R1 Distill 70B (DeepSeek / Groq)", get_deepseek_llm),
    ("QwQ 32B (Qwen·Alibaba / Groq)",         get_qwq_llm),
]
