"""FastAPI backend for AEO Diagnostic.

Development:  uvicorn api:app --reload --port 8000
Production:   uvicorn api:app --host 0.0.0.0 --port 8080
  (the Dockerfile and fly.toml handle production startup)
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
from dataclasses import asdict
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

app = FastAPI(title="AEO Diagnostic API", version="1.0.0")

# CORS only needed when the frontend dev server runs on a different port (localhost:3000).
# In production the frontend is served from the same origin so CORS is not required.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response schemas ────────────────────────────────────────────────

class RunRequest(BaseModel):
    query: str
    target: str
    verify_citations: bool = True
    deep_analysis: bool = False


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _card_to_dict(card) -> dict:
    """Convert ScoreCard dataclass to a JSON-serialisable dict."""
    d = asdict(card)
    # avg_position may be None — keep as-is (JSON null)
    return d


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "groq_key_set": bool(os.environ.get("GROQ_API_KEY"))}


@app.post("/api/run")
async def run_diagnostic(req: RunRequest):
    """Run a full AEO diagnostic and stream progress events via SSE."""

    async def generate():
        try:
            from src.clients import query_all
            from src.scorer import score_panel
            from src.agents import run_deep_analysis

            if not os.environ.get("GROQ_API_KEY"):
                yield _sse({"type": "error", "message": "GROQ_API_KEY is not set."})
                return

            yield _sse({"type": "status", "message": "Querying 6 LLMs (Meta · OpenAI · Alibaba)…"})
            responses = await asyncio.to_thread(query_all, req.query)

            yield _sse({"type": "status", "message": "Scoring results and verifying citations…"})
            card = await asyncio.to_thread(
                score_panel, req.target, req.query, responses, req.verify_citations
            )

            deep_text: Optional[str] = None
            if req.deep_analysis:
                yield _sse({"type": "status", "message": "Running deep agent analysis…"})
                deep_text = await asyncio.to_thread(
                    run_deep_analysis,
                    req.target,
                    req.query,
                    card.avg_position,
                    card.per_model,
                )

            result = _card_to_dict(card)
            if deep_text is not None:
                result["deep_analysis"] = deep_text

            # Include raw response labels + latency for the expander
            result["raw_responses"] = [
                {
                    "model_label": r.model_label,
                    "latency_ms": r.latency_ms,
                    "text": r.text,
                    "error": r.error,
                }
                for r in responses
            ]

            yield _sse({"type": "result", "data": result})

        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Serve Next.js static export in production ─────────────────────────────────
# The Dockerfile copies frontend/out/ into the image alongside api.py.
# When that directory is present (production), FastAPI serves the frontend
# from the same origin — no CORS, no separate server needed.
# In local dev the directory is absent; run `npm run dev` in frontend/ instead.

_static_dir = pathlib.Path(__file__).parent / "frontend" / "out"
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
