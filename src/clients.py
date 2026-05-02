"""AI model clients — OpenAI GPT-4o, Anthropic Claude, Google Gemini."""

from __future__ import annotations

import os
from .models import ModelResult

# ── prompt sent to every model ────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
A consumer is researching: "{query}"

Please give your top 8–10 recommendations, ranked #1 (best) to #8–10.
Use this exact format for every entry:

1. **Brand Product Name** – one sentence on why it stands out
2. **Brand Product Name** – one sentence on why it stands out
…

Be specific with real brand and product names. Do not add extra sections.\
"""

# ── optional SDK imports ──────────────────────────────────────────────────────
try:
    import openai as _openai
except ImportError:
    _openai = None  # type: ignore[assignment]

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None  # type: ignore[assignment]

try:
    import google.generativeai as _genai
except ImportError:
    _genai = None  # type: ignore[assignment]


def query_openai(query: str) -> ModelResult:
    result = ModelResult(model_name="GPT-4o (OpenAI)")
    if _openai is None:
        result.error = "openai package not installed"
        return result
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        result.error = "OPENAI_API_KEY not set"
        return result
    try:
        client = _openai.OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(query=query)}],
            temperature=0.3,
            max_tokens=1200,
        )
        result.raw_response = resp.choices[0].message.content or ""
    except Exception as exc:
        result.error = str(exc)
    return result


def query_claude(query: str) -> ModelResult:
    result = ModelResult(model_name="Claude Sonnet (Anthropic)")
    if _anthropic is None:
        result.error = "anthropic package not installed"
        return result
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        result.error = "ANTHROPIC_API_KEY not set"
        return result
    try:
        client = _anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(query=query)}],
        )
        result.raw_response = resp.content[0].text
    except Exception as exc:
        result.error = str(exc)
    return result


def query_gemini(query: str) -> ModelResult:
    result = ModelResult(model_name="Gemini 1.5 Pro (Google)")
    if _genai is None:
        result.error = "google-generativeai package not installed"
        return result
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        result.error = "GEMINI_API_KEY not set"
        return result
    try:
        _genai.configure(api_key=key)
        model = _genai.GenerativeModel("gemini-1.5-pro")
        resp = model.generate_content(PROMPT_TEMPLATE.format(query=query))
        result.raw_response = resp.text
    except Exception as exc:
        result.error = str(exc)
    return result


ALL_CLIENTS = [query_openai, query_claude, query_gemini]
