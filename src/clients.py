"""LLM panel client — wraps LangChain chains behind a simple query_all() API.

The chain returns raw LLM text; parsing happens downstream in scorer.py so
every model's response format (numbered lists, bullets, prose) is handled
uniformly by the regex parser in parser.py.
"""

from __future__ import annotations

import time

from .chains import ALL_LLM_CONFIGS, build_ranking_chain
from .models import ModelResponse, ModelResult


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
                raw_text: str = chain.invoke({"query": query})
                resp.latency_ms = int((time.time() - t0) * 1000)
                if not raw_text or not raw_text.strip():
                    resp.error = "Model returned an empty response"
                    print(f"✗  empty response in {resp.latency_ms} ms")
                else:
                    resp.text = raw_text
                    print(f"✓  {len(raw_text)} chars in {resp.latency_ms} ms")
        except Exception as exc:
            resp.error = str(exc)
            resp.latency_ms = int((time.time() - t0) * 1000)
            print(f"✗  {exc}")
        responses.append(resp)

    return responses


# ── Legacy adapter kept for any direct imports of ALL_CLIENTS ─────────────────

def _legacy_client(label: str, get_llm_fn):
    def _client(query: str) -> ModelResult:
        result = ModelResult(model_name=label)
        try:
            llm = get_llm_fn()
            if llm is None:
                result.error = "API key not configured"
                return result
            chain = build_ranking_chain(llm)
            result.raw_response = chain.invoke({"query": query}) or ""
        except Exception as exc:
            result.error = str(exc)
        return result
    _client.__name__ = f"query_{label.split()[0].lower()}"
    return _client


ALL_CLIENTS = [_legacy_client(label, fn) for label, fn in ALL_LLM_CONFIGS]
