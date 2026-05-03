"""LLM panel client — wraps LangChain chains behind a simple query_all() API.

query_all(query) → list[ModelResponse]   ← used by app.py and the CLI
ALL_CLIENTS                              ← legacy list of callables (kept for compat)
"""

from __future__ import annotations

import time

from .chains import ALL_LLM_CONFIGS, build_ranking_chain
from .models import ModelResponse, ModelResult, LLMRankingOutput


def query_all(query: str) -> list[ModelResponse]:
    """Query every model in the panel and return raw ModelResponse objects."""
    responses: list[ModelResponse] = []

    for label, get_llm in ALL_LLM_CONFIGS:
        t0 = time.time()
        resp = ModelResponse(model_label=label)
        print(f"  → Querying {label} … ", end="", flush=True)
        try:
            llm = get_llm()
            if llm is None:
                resp.error = "API key not configured"
                print("✗  (no API key)")
            else:
                chain = build_ranking_chain(llm)
                output: LLMRankingOutput = chain.invoke({"query": query})
                resp.text = "\n".join(
                    f"{p.rank}. **{p.name}** – {p.description}"
                    for p in output.products
                )
                resp.latency_ms = int((time.time() - t0) * 1000)
                print(f"✓  {len(resp.text)} chars in {resp.latency_ms} ms")
        except Exception as exc:
            resp.error = str(exc)
            resp.latency_ms = int((time.time() - t0) * 1000)
            print(f"✗  {exc}")
        responses.append(resp)

    return responses


# ── Legacy adapter for old aeo_diagnostic.py imports ─────────────────────────

def _legacy_client(label: str, get_llm_fn):
    """Wrap a LangChain LLM factory into the old ModelResult-returning signature."""
    def _client(query: str) -> ModelResult:
        result = ModelResult(model_name=label)
        try:
            llm = get_llm_fn()
            if llm is None:
                result.error = "API key not configured"
                return result
            chain = build_ranking_chain(llm)
            output: LLMRankingOutput = chain.invoke({"query": query})
            result.raw_response = "\n".join(
                f"{p.rank}. **{p.name}** – {p.description}"
                for p in output.products
            )
        except Exception as exc:
            result.error = str(exc)
        return result

    _client.__name__ = f"query_{label.split()[0].lower()}"
    return _client


ALL_CLIENTS = [_legacy_client(label, fn) for label, fn in ALL_LLM_CONFIGS]
