# AEO Diagnostic

[![Live Demo](https://img.shields.io/badge/Live_Demo-aeo--diagnostic-4CC61E?style=for-the-badge&logo=fly.io&logoColor=white)](https://pallavikailas-aeo.fly.dev)
[![Deploy](https://github.com/pallavikailas/Product-Ranking-aeo/actions/workflows/deploy.yml/badge.svg)](https://github.com/pallavikailas/Product-Ranking-aeo/actions/workflows/deploy.yml)
[![AEO Diagnostic](https://github.com/pallavikailas/Product-Ranking-aeo/actions/workflows/aeo_diagnostic.yml/badge.svg)](https://github.com/pallavikailas/Product-Ranking-aeo/actions/workflows/aeo_diagnostic.yml)

> **AEO = Answer Engine Optimization.** When a shopper asks an AI assistant *"best magnesium supplement for seniors"*, where does your brand actually rank? This tool finds out — across **six independent LLMs** — and verifies every citation against the open web.

## Live demo

**[→ https://pallavikailas-aeo.fly.dev](https://pallavikailas-aeo.fly.dev)**

---

## Why

SEO told brands how they ranked on Google. **AEO** is the same question for the AI era: how do you rank on ChatGPT, Claude, Gemini, and the new wave of AI shopping assistants? Brands have no visibility into this today. This is the diagnostic step.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Next.js 14 + TypeScript  (frontend/)                    │
│  Served as a static export by the FastAPI process        │
└────────────────────────┬─────────────────────────────────┘
                         │  SSE stream  /api/run
┌────────────────────────▼─────────────────────────────────┐
│  FastAPI  (api.py)                                       │
│  POST /api/run  →  streams progress + final ScoreCard    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  LangChain Chains  (src/chains.py)                       │
│  One prompt, six LLMs on Groq — free, fast inference     │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  LangGraph Pipeline  (src/graph.py)                      │
│  START → query_panel → extract_brands                    │
│              └─(conditional)─► verify_citations          │
│                                      └─► compute_score   │
│                                                END       │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  Deep Research Agent  (src/agents.py)                    │
│  LangGraph ReAct agent with three tools:                 │
│    • search_brand_presence    (DuckDuckGo web check)     │
│    • analyze_aeo_gap          (rank-aware recommendations│
│    • analyze_temporal_context (training cutoff vs.       │
│                                live web-search models)   │
└──────────────────────────────────────────────────────────┘
```

## What it does

1. **LangChain** sends a shopper query to a panel of **six LLMs** via Groq:

   | Model | Company | Knowledge cutoff |
   |---|---|---|
   | Llama 3.3 70B | Meta | Dec 2023 |
   | GPT-OSS 120B | OpenAI | Mar 2024 |
   | Llama 4 Scout 17B | Meta | Mar 2025 |
   | Llama 3.1 8B Instant | Meta | Dec 2023 |
   | GPT-OSS 20B | OpenAI | Mar 2024 |
   | Qwen3 32B | Alibaba | Sep 2024 |

2. **LangGraph** orchestrates parse → verify → score with a conditional branch that skips web verification when requested.
3. Parses each reply to find the target brand, its **rank**, and the **sentiment** of surrounding text.
4. Extracts all cited brands and **verifies each against DuckDuckGo** to catch hallucinations.
5. Optionally runs a **LangGraph ReAct deep agent** that:
   - Verifies real-world brand presence
   - Compares **training cutoff dates** across models (or flags if a model has live web search, making cutoffs irrelevant)
   - Generates targeted AEO recommendations based on temporal patterns
6. Streams live progress to the frontend via **Server-Sent Events**, then delivers a full **A–F report card** with colour-graded stats.

## Stack

| Component | Tool |
|---|---|
| Frontend | **Next.js 14** + TypeScript + Tailwind CSS |
| API server | **FastAPI** + SSE streaming |
| LLM panel (6 models) | **Groq API** + **LangChain** |
| Pipeline orchestration | **LangGraph** — `StateGraph` with conditional routing |
| Deep research agent | **LangGraph ReAct** — `create_react_agent` + custom tools |
| Citation verifier | **DuckDuckGo** — `ddgs` + Llama 3.3 70B brand extraction |
| Deployment | **Fly.io** — single Docker container (Node build → Python runtime) |
| CI / scheduled runs | **GitHub Actions** |
| Tests | **pytest** |

## Scoring formula

```
overall = 0.45 × mention_rate × 100    (was brand mentioned at all?)
        + 0.30 × position_score        (1st = 100, 5th = 20, absent = 0)
        + 0.15 × sentiment_score       (−1…+1 mapped to 0…100)
        + 0.10 × citation_score        (% of cited brands findable on DDG)
```

Grades: **A+** ≥ 90 · **A** ≥ 80 · **B** ≥ 70 · **C** ≥ 55 · **D** ≥ 40 · **F** > 0

---

## Deployment (no local setup required)

Everything runs inside GitHub Actions. The workflow creates the Fly.io app, sets secrets, builds the Docker image remotely, deploys, and writes the live-URL badge back into this README — all automatically on every push to `main`.

**You only need to add two secrets once, entirely through your browser:**

### Step 1 — Get a Fly.io API token (2 minutes, browser only)

1. Sign up at **[fly.io](https://fly.io)** (free; a credit card is required for identity verification but the hobby tier is $0/month).
2. Go to **[fly.io/user/personal_access_tokens](https://fly.io/user/personal_access_tokens)** → **Create token** → copy it.

### Step 2 — Get a Groq API key (1 minute, browser only)

1. Sign up at **[console.groq.com](https://console.groq.com)** (free).
2. Go to **API Keys** → **Create API Key** → copy it.

### Step 3 — Add both secrets to GitHub (1 minute, browser only)

In this repository: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `FLY_API_TOKEN` | The Fly.io token from Step 1 |
| `GROQ_API_KEY` | The Groq key from Step 2 |

### Step 4 — Push to main (or trigger manually)

Push any commit to `main`, or go to **Actions → Deploy → Run workflow**.

GitHub Actions will:
1. Run unit tests
2. Create the Fly.io app `pallavikailas-aeo` (only on the first run)
3. Sync `GROQ_API_KEY` as a Fly.io secret
4. Build the Docker image on Fly.io's remote builders (no local Docker needed)
5. Deploy — live at **[https://pallavikailas-aeo.fly.dev](https://pallavikailas-aeo.fly.dev)**
6. Commit the live-URL badge back into this README

Every subsequent push auto-redeploys. That's it.

---

## Local development (optional)

### Backend

```bash
git clone https://github.com/pallavikailas/Product-Ranking-aeo.git
cd Product-Ranking-aeo
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."
uvicorn api:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # sets NEXT_PUBLIC_API_URL=http://localhost:8000
npm install && npm run dev
# UI at http://localhost:3000
```

### CLI

```bash
python aeo_diagnostic.py \
  --query  "best magnesium supplement for seniors" \
  --target "Nature Made" \
  --deep-analysis
```

---

## Scheduled AEO reports

The `aeo_diagnostic.yml` workflow runs the CLI automatically:

| Trigger | When |
|---|---|
| Push to `main` | Every push |
| Manual dispatch | Any time, with custom query/target |
| Schedule | Every Monday 09:00 UTC |

Reports are uploaded as workflow artifacts (90-day retention) and committed back to `reports/`.

---

## Repo layout

```
Product-Ranking-aeo/
├── api.py                       # FastAPI server + SSE streaming
├── aeo_diagnostic.py            # CLI entry point
├── app.py                       # Streamlit UI (local fallback)
├── Dockerfile                   # Multi-stage: Node (Next.js) → Python (FastAPI)
├── fly.toml                     # Fly.io configuration
├── requirements.txt
├── frontend/                    # Next.js 14 TypeScript app
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx             # Main diagnostic page
│   │   └── globals.css
│   ├── lib/types.ts             # TypeScript types
│   └── .env.local.example
├── src/
│   ├── chains.py                # LangChain chains (6 Groq models)
│   ├── graph.py                 # LangGraph StateGraph pipeline
│   ├── agents.py                # ReAct deep-research agent + temporal analysis
│   ├── clients.py               # query_all()
│   ├── scorer.py                # score_panel() → ScoreCard
│   ├── web_verifier.py          # DuckDuckGo citation verifier
│   ├── models.py                # Dataclasses + Pydantic models
│   ├── parser.py                # Regex ranked-list parser
│   └── report.py                # HTML + JSON report writer
├── tests/
│   └── test_scorer.py           # Offline pytest (no API key needed)
└── .github/workflows/
    ├── deploy.yml               # Test + auto-deploy to Fly.io
    └── aeo_diagnostic.yml       # Scheduled AEO diagnostic runs
```

## License

MIT.
