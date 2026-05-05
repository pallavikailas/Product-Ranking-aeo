# AEO Diagnostic

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://brand-aeo.streamlit.app/)
[![CI](https://github.com/pallavikailas/Product-Ranking-aeo/actions/workflows/aeo_diagnostic.yml/badge.svg)](https://github.com/pallavikailas/Product-Ranking-aeo/actions/workflows/aeo_diagnostic.yml)


> **AEO = Answer Engine Optimization.** When a shopper asks an AI assistant *"best magnesium supplement for seniors"*, where does your brand actually rank? This tool finds out — across three independent LLMs — and verifies every citation against the open web.

https://github.com/user-attachments/assets/6ea4251a-8983-459d-91ca-c50df06f85b0

## Why

SEO told brands how they ranked on Google. **AEO** is the same question for the AI era: how do you rank on ChatGPT, Claude, Gemini, and the new wave of shopping assistants? Brands have no visibility into this today. This is the diagnostic step.

## Architecture

The pipeline is built on three layers:

```
┌─────────────────────────────────────────────────────────┐
│  LangChain Chains  (src/chains.py)                      │
│  Unified prompt + LLM interface for GPT-4o, Claude,     │
│  and Gemini — one chain definition runs all three.      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  LangGraph Pipeline  (src/graph.py)                     │
│                                                         │
│  START → query_panel → extract_brands                   │
│              └─(conditional)─► verify_citations         │
│                                      └─► compute_score  │
│                                                END      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Deep Research Agent  (src/agents.py)                   │
│  LangGraph ReAct agent with tools:                      │
│    • search_brand_presence  (DuckDuckGo web check)      │
│    • analyze_aeo_gap        (structured recommendations)│
└─────────────────────────────────────────────────────────┘
```

## What it does

1. **LangChain** sends a shopper query to a panel of **6 LLMs** via Groq — free, fast inference:
2. **LangGraph** orchestrates the pipeline: query → parse → verify → score, with a conditional branch that skips web verification when `--no-verify` is passed.
3. Parses each reply to find the target brand, its **rank**, and the **sentiment** of the surrounding text.
4. Extracts all cited brands and **verifies each against DuckDuckGo** to catch hallucinations.
5. Optionally runs a **LangGraph ReAct deep agent** that investigates brand presence and generates targeted AEO recommendations.
6. Outputs a **report card** (HTML + JSON) with an A–F grade and per-model breakdown.

## Stack

| Component                | Tool                                                                      | 
|--------------------------|---------------------------------------------------------------------------|
| LLM panel (6 models)     | **Groq API** + **LangChain** — `langchain-groq`                           |
| Pipeline orchestration   | **LangGraph** — `StateGraph` with conditional routing                     |
| Deep research agent      | **LangGraph ReAct** — `create_react_agent` + custom tools                 |
| Citation verifier        | **DuckDuckGo HTML** — `requests` + `bs4`                                  |
| UI                       | **Streamlit**                                                             |
| CI / scheduled runs      | **GitHub Actions**                                                        |
| Tests                    | **pytest**                                                                |

## Scoring formula

```
overall = 0.45 × mention_rate × 100    (was brand mentioned at all?)
        + 0.30 × position_score        (1st = 100, 5th = 20, absent = 0)
        + 0.15 × sentiment_score       (−1…+1 mapped to 0…100)
        + 0.10 × citation_score        (% of cited brands findable on DDG)
```

Bands: **A+** ≥ 90 · **A** ≥ 80 · **B** ≥ 70 · **C** ≥ 55 · **D** ≥ 40 · **F** > 0.

## Repo layout

```
aeo-diagnostic/
├── aeo_diagnostic.py           # CLI entry point
├── app.py                      # Streamlit UI
├── src/
│   ├── chains.py               # LangChain prompt chains (NEW)
│   ├── graph.py                # LangGraph pipeline (NEW)
│   ├── agents.py               # LangGraph ReAct deep-research agent (NEW)
│   ├── clients.py              # query_all() — calls LangChain chains
│   ├── scorer.py               # score_panel() — aggregates ScoreCard
│   ├── web_verifier.py         # DuckDuckGo citation verifier (NEW)
│   ├── models.py               # Dataclasses + Pydantic output models
│   ├── parser.py               # Regex-based ranked-list parser
│   ├── scoring.py              # Scoring helpers (legacy compat)
│   └── report.py               # HTML + JSON report writer
├── tests/
│   └── test_scorer.py          # Offline unit tests (pytest)
├── .github/workflows/
│   └── aeo_diagnostic.yml      # CI + on-demand diagnostic runs
├── requirements.txt
└── reports/                    # Generated reports land here
```

## LangGraph pipeline detail

```
AEOState
  query, target_brand, verify_citations
  ↓
query_panel          ← LangChain chain per model (GPT-4o / Claude / Gemini)
  raw_responses[]
  ↓
extract_brands       ← pull unique brand names from all responses
  all_brands[]
  ↓  (conditional)
verify_citations     ← DuckDuckGo POST for each brand          ┐
  verifications[]                                              │ skipped if
  ↓                                                            │ --no-verify
compute_score        ← aggregate mention rate, position,       ┘
  score_card           sentiment, citation score → ScoreCard
```

## Deep Agent (LangGraph ReAct)

Pass `--deep-analysis` on the CLI (or toggle in the Streamlit sidebar) to activate a **ReAct agent** that:

1. Calls `search_brand_presence` — hits DuckDuckGo to confirm the brand is a real entity
2. Calls `analyze_aeo_gap` — generates structured, rank-aware improvement recommendations
3. Synthesises findings into a markdown report

The agent uses `llama-3.3-70b-versatile` via Groq (same `GROQ_API_KEY`).

## Running autonomously

The included GitHub Actions workflow has two jobs that run on **every push to `main`**, on `workflow_dispatch`, and on the weekly Monday schedule:

| Job | Trigger | Needs secret? |
|-----|---------|---------------|
| **`test`** | every push | No |
| **`diagnostic`** | every push (after tests pass) | `GROQ_API_KEY` |

