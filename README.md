# AEO Diagnostic

Answer Engine Optimization (AEO) diagnostic tool that queries **GPT-4o**, **Claude Sonnet**, and **Gemini 1.5 Pro** with the same product search query and produces a scored report card showing how your brand ranks versus competitors across all three AI answer engines.

---

## How it works

```
User query + target brand
        │
        ├─► OpenAI GPT-4o
        ├─► Anthropic Claude Sonnet
        └─► Google Gemini 1.5 Pro
                │
                ▼
        Parse ranked product lists
        Find target brand position
        Score sentiment context
                │
                ▼
        HTML + JSON report card
        (grade A+–F, competitor table, share-of-voice, recommendations)
```

**Scoring (per model, 0–100):**
| Component | Weight |
|---|---|
| Brand mentioned at all | 40 pts |
| Rank quality (1st = 40, each step −5) | 40 pts |
| Contextual sentiment (-1…+1 → 0–20) | 20 pts |

The overall grade is the average across all three models.

---

## Project structure

```
├── aeo_diagnostic.py          # CLI entry point
├── src/
│   ├── clients.py             # OpenAI / Claude / Gemini API wrappers
│   ├── models.py              # Shared data classes
│   ├── parser.py              # Ranked list extraction + sentiment
│   ├── scoring.py             # Score, grade, competitor aggregation
│   └── report.py              # HTML + JSON report generation
├── reports/                   # Generated reports (committed by CI)
├── requirements.txt
└── .github/workflows/
    └── aeo_diagnostic.yml     # GitHub Actions workflow
```

---

## Local usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API keys

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="AIza..."
```

Or create a `.env` file (never commit it — it's in `.gitignore`).

### 3. Run

```bash
python aeo_diagnostic.py \
  --query "best magnesium supplement for seniors" \
  --brand "Nature Made" \
  --output-dir reports/
```

Reports are written to `reports/aeo_<brand>_<date>.html` and `.json`.

---

## GitHub Actions (hosted pipeline)

The workflow at [.github/workflows/aeo_diagnostic.yml](.github/workflows/aeo_diagnostic.yml) runs two ways:

| Trigger | When |
|---|---|
| **Manual** (`workflow_dispatch`) | Run from the **Actions** tab with custom query + brand |
| **Scheduled** | Every Monday 09:00 UTC with default values |

### Setup (one-time)

Add three repository secrets in **Settings → Secrets and variables → Actions**:

| Secret name | Where to get it |
|---|---|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) |

After each run:
- The HTML + JSON report is uploaded as a **workflow artifact** (retained 90 days).
- The report is also **committed back to the repo** under `reports/` for a browsable history.

---

## Output

The HTML report includes:
- **Overall AEO grade** (A+ to F) and score bar
- **Per-model breakdown** — rank, sentiment, full ranked list with target highlighted
- **Competitor table** — best rank, total mentions, share of voice across all 3 models
- **Recommendations** — actionable steps to improve visibility
