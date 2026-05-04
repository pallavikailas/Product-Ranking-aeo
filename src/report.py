"""HTML and JSON report generation for AEO diagnostic results."""

from __future__ import annotations

import json
import os

from .models import AEOReport, ModelResult
from .scoring import score_model_result

# ── grade palette ─────────────────────────────────────────────────────────────
_GRADE_COLOR = {
    "A+": "#00c853", "A": "#43a047", "B": "#8bc34a",
    "C": "#ff9800", "D": "#ef6c00", "F": "#c62828", "N/A": "#9e9e9e",
}

_CSS = """
:root {
  --bg:#f5f7fa; --card:#fff; --border:#e2e8f0;
  --text:#1a202c; --muted:#718096; --accent:#4f46e5;
  --target-bg:#fff7ed; --target-border:#f97316;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     background:var(--bg);color:var(--text);padding:24px}

/* header */
.header{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
        color:#fff;border-radius:16px;padding:32px;margin-bottom:24px}
.header h1{font-size:1.6rem;font-weight:700;margin-bottom:8px}
.header .meta{opacity:.75;font-size:.9rem}

/* score strip */
.score-strip{display:flex;gap:20px;margin-bottom:24px;flex-wrap:wrap}
.grade-box{border-radius:16px;width:120px;height:120px;display:flex;
           flex-direction:column;align-items:center;justify-content:center;
           flex-shrink:0;color:#fff}
.grade-box .letter{font-size:3rem;font-weight:900;line-height:1}
.grade-box .lbl{font-size:.8rem;opacity:.9;margin-top:4px}
.score-detail{background:var(--card);border:1px solid var(--border);
              border-radius:16px;padding:24px;flex:1;min-width:240px}
.score-detail h2{font-size:.85rem;text-transform:uppercase;letter-spacing:.06em;
                 color:var(--muted);margin-bottom:12px}
.score-num{font-size:2.5rem;font-weight:800}
.bar-wrap{background:#e2e8f0;border-radius:8px;height:12px;margin-top:12px;overflow:hidden}
.bar-fill{height:100%;border-radius:8px;
          background:linear-gradient(90deg,#ef4444 0%,#f97316 40%,#22c55e 100%)}
.pills{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.pill{padding:4px 12px;border-radius:99px;font-size:.8rem;font-weight:600}
.pill-green{background:#dcfce7;color:#15803d}
.pill-amber{background:#fef9c3;color:#854d0e}
.pill-red{background:#fee2e2;color:#b91c1c}

/* section */
section{margin-bottom:28px}
section h2{font-size:1.1rem;font-weight:700;margin-bottom:14px;
           padding-bottom:8px;border-bottom:2px solid var(--border)}

/* badges */
.badge{padding:3px 10px;border-radius:99px;font-size:.75rem;font-weight:600}
.badge-rank{background:#dbeafe;color:#1d4ed8}
.badge-mention{background:#fef9c3;color:#854d0e}
.badge-miss{background:#f3f4f6;color:#6b7280}
.badge-err{background:#fee2e2;color:#b91c1c}

/* model cards */
.model-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.model-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px}
.model-card.err{opacity:.6}
.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.card-name{font-weight:700;font-size:.95rem}
.card-meta{display:flex;gap:16px;font-size:.82rem;color:var(--muted);margin-bottom:12px}
.product-list{list-style:none;padding:0;font-size:.82rem;max-height:230px;overflow-y:auto}
.product-list li{padding:4px 6px;border-radius:6px;margin-bottom:2px;line-height:1.4}
.product-list li.hi{background:var(--target-bg);
                    border-left:3px solid var(--target-border);padding-left:8px}
.raw-toggle{margin-top:12px;font-size:.8rem}
.raw-toggle summary{cursor:pointer;color:var(--muted)}
.raw-toggle pre{background:#f8fafc;border:1px solid var(--border);border-radius:8px;
                padding:10px;margin-top:8px;white-space:pre-wrap;font-size:.75rem;
                max-height:200px;overflow-y:auto}

/* competitor table */
.comp-table{width:100%;border-collapse:collapse;background:var(--card);
            border:1px solid var(--border);border-radius:12px;overflow:hidden;font-size:.88rem}
.comp-table th{background:#f8fafc;padding:10px 14px;text-align:left;font-weight:600;
               color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.05em}
.comp-table td{padding:9px 14px;border-top:1px solid var(--border)}
.comp-table tr.hi td{background:var(--target-bg);font-weight:700}
.sov-wrap{display:flex;align-items:center;gap:8px}
.sov-bar{height:8px;border-radius:4px;background:var(--accent);min-width:4px}
.sov-wrap span{font-size:.8rem;color:var(--muted)}

/* recommendations */
.rec-box{background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:20px}
.rec-box ul{padding-left:20px}
.rec-box li{margin-bottom:8px;font-size:.9rem;line-height:1.5}

/* footer */
footer{text-align:center;color:var(--muted);font-size:.8rem;margin-top:32px}
"""


# ── helpers ───────────────────────────────────────────────────────────────────
def _badge(r: ModelResult) -> str:
    if r.error:
        return '<span class="badge badge-err">Error</span>'
    if r.target_rank:
        return f'<span class="badge badge-rank">Ranked #{r.target_rank}</span>'
    if r.target_mentioned:
        return '<span class="badge badge-mention">Mentioned</span>'
    return '<span class="badge badge-miss">Not found</span>'


def _sentiment_label(s: float) -> str:
    if s > 0.2:
        return "Positive 😊"
    if s < -0.2:
        return "Negative 😟"
    return "Neutral 😐"


def _recommendations(report: AEOReport) -> str:
    mention_count = sum(
        1 for r in report.results if r.target_mentioned and not r.error
    )
    missing = [r.model_name for r in report.results if not r.target_mentioned and not r.error]
    ranked = [r.target_rank for r in report.results if r.target_rank]
    avg_rank = round(sum(ranked) / len(ranked), 1) if ranked else None

    items: list[str] = []
    if missing:
        items.append(
            f"<li>Brand absent from <strong>{', '.join(missing)}</strong>. "
            "Publish detailed product pages, third-party reviews, and schema markup to improve coverage.</li>"
        )
    if avg_rank and avg_rank > 3:
        items.append(
            f"<li>Average rank is <strong>#{avg_rank}</strong>. "
            "Create comparison content and earn authoritative backlinks to push into the top 3.</li>"
        )
    if mention_count == 0:
        items.append(
            "<li>No mentions detected at all. Start with authoritative reviews, "
            "FAQ pages, and structured data (JSON-LD) so AI engines can surface your brand.</li>"
        )
    if not items:
        items.append(
            "<li>Strong visibility across all models. "
            "Maintain freshness of product pages and monitor for emerging competitors.</li>"
        )
    return "<ul>" + "".join(items) + "</ul>"


# ── main export functions ─────────────────────────────────────────────────────
def build_html(report: AEOReport, target_brand_lower: str) -> str:
    """Return a self-contained HTML report as a string."""
    grade_color = _GRADE_COLOR.get(report.grade, "#9e9e9e")
    score_pct = min(100, max(0, report.overall_score))
    ts = report.timestamp.replace("T", " ").replace("Z", " UTC")

    # ── model cards ───────────────────────────────────────────────────────────
    cards_html = ""
    for r in report.results:
        model_score = round(score_model_result(r), 1)
        products_html = ""
        for p in r.products[:10]:
            css = ' class="hi"' if target_brand_lower in p.name.lower() else ""
            products_html += (
                f"<li{css}><b>#{p.rank} {p.name}</b> — {p.description}</li>"
            )
        raw_esc = (r.raw_response or r.error or "").replace("<", "&lt;").replace(">", "&gt;")
        cards_html += f"""
<div class="model-card{'  err' if r.error else ''}">
  <div class="card-head">
    <span class="card-name">{r.model_name}</span>
    {_badge(r)}
  </div>
  <div class="card-meta">
    <span>Score <strong>{model_score}/100</strong></span>
    <span>Sentiment <strong>{_sentiment_label(r.sentiment_score)}</strong></span>
  </div>
  <ol class="product-list">{products_html}</ol>
  <details class="raw-toggle">
    <summary>Raw response</summary>
    <pre>{raw_esc}</pre>
  </details>
</div>"""

    # ── competitor rows ───────────────────────────────────────────────────────
    comp_rows = ""
    for brand_key, data in list(report.competitors.items())[:12]:
        is_target = target_brand_lower in brand_key.lower()
        row_cls = ' class="hi"' if is_target else ""
        best = f"#{data['best_rank']}" if data["best_rank"] else "–"
        bar_w = min(100, data["sov"] * 3)
        comp_rows += f"""
<tr{row_cls}>
  <td>{data['display']}</td>
  <td>{best}</td>
  <td>{data['mentions']}</td>
  <td><div class="sov-wrap">
    <div class="sov-bar" style="width:{bar_w:.0f}px"></div>
    <span>{data['sov']}%</span>
  </div></td>
</tr>"""

    # ── mention pills ─────────────────────────────────────────────────────────
    mention_count = sum(1 for r in report.results if r.target_mentioned and not r.error)
    ranked_vals = [r.target_rank for r in report.results if r.target_rank]
    avg_rank_str = f"Avg rank #{round(sum(ranked_vals)/len(ranked_vals),1)}" if ranked_vals else "No ranked mentions"
    rank_pill_cls = "pill-green" if ranked_vals and sum(ranked_vals)/len(ranked_vals) <= 3 else "pill-amber" if ranked_vals else "pill-red"

    rec_html = _recommendations(report)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEO Report — {report.target_brand}</title>
<style>{_CSS}</style>
</head>
<body>

<div class="header">
  <h1>AEO Diagnostic Report</h1>
  <p class="meta">
    Query: <strong>"{report.query}"</strong>&nbsp;·&nbsp;
    Target: <strong>{report.target_brand}</strong>&nbsp;·&nbsp;
    {ts}
  </p>
</div>

<div class="score-strip">
  <div class="grade-box" style="background:{grade_color}">
    <span class="letter">{report.grade}</span>
    <span class="lbl">AEO Grade</span>
  </div>
  <div class="score-detail">
    <h2>Overall AEO Score</h2>
    <span class="score-num" style="color:{grade_color}">{report.overall_score}</span>
    <span style="color:var(--muted)">/100</span>
    <div class="bar-wrap">
      <div class="bar-fill" style="width:{score_pct:.0f}%"></div>
    </div>
    <div class="pills">
      <span class="pill pill-{'green' if mention_count == 3 else 'amber' if mention_count > 0 else 'red'}">
        Mentioned in {mention_count}/3 models
      </span>
      <span class="pill {rank_pill_cls}">{avg_rank_str}</span>
    </div>
  </div>
</div>

<section>
  <h2>Model-by-Model Breakdown</h2>
  <div class="model-grid">{cards_html}</div>
</section>

<section>
  <h2>Competitor Analysis — All Models Combined</h2>
  <table class="comp-table">
    <thead>
      <tr>
        <th>Brand / Product</th><th>Best Rank</th>
        <th>Total Mentions</th><th>Share of Voice</th>
      </tr>
    </thead>
    <tbody>{comp_rows}</tbody>
  </table>
</section>

<section>
  <h2>Recommendations</h2>
  <div class="rec-box">{rec_html}</div>
</section>

<footer>
  Generated by <strong>AEO Diagnostic</strong> &mdash;
  OpenAI GPT-4o · Anthropic Claude Sonnet · Google Gemini 1.5 Pro
</footer>
</body>
</html>"""


def save_html(report: AEOReport, target_brand_lower: str, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_html(report, target_brand_lower))
    print(f"   HTML → {path}")


def save_json(report: AEOReport, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = {
        "query": report.query,
        "target_brand": report.target_brand,
        "timestamp": report.timestamp,
        "overall_score": report.overall_score,
        "grade": report.grade,
        "competitors": report.competitors,
        "models": [
            {
                "model": r.model_name,
                "error": r.error,
                "target_mentioned": r.target_mentioned,
                "target_rank": r.target_rank,
                "sentiment_score": r.sentiment_score,
                "products": [
                    {"rank": p.rank, "name": p.name, "description": p.description}
                    for p in r.products
                ],
                "raw_response": r.raw_response,
            }
            for r in report.results
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"   JSON → {path}")


# ── ScoreCard report writer (used by app.py and the new CLI) ──────────────────

def write_reports(card, out_dir) -> tuple:
    """Write HTML + JSON from a ScoreCard. Returns (html_path, json_path) as Path objects."""
    import re
    import datetime
    from pathlib import Path
    from .models import ScoreCard

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", card.target.lower()).strip("-")
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    base = out_dir / f"aeo_{slug}_{date_str}"
    html_path = base.with_suffix(".html")
    json_path = base.with_suffix(".json")

    html_path.write_text(_scorecard_html(card), encoding="utf-8")
    json_path.write_text(
        json.dumps(_scorecard_json(card), indent=2), encoding="utf-8"
    )
    return html_path, json_path


def _scorecard_json(card) -> dict:
    return {
        "query": card.query,
        "target": card.target,
        "overall": card.overall,
        "grade": card.grade,
        "mention_rate": card.mention_rate,
        "avg_position": card.avg_position,
        "sentiment_score": card.sentiment_score,
        "citation_score": card.citation_score,
        "per_model": [
            {
                "model": m.model_label,
                "mentioned": m.mentioned,
                "position": m.position,
                "sentiment": m.sentiment,
                "competitors": m.competitors,
                "error": m.error,
            }
            for m in card.per_model
        ],
        "verifications": card.verifications,
    }


def _scorecard_html(card) -> str:
    grade_color = _GRADE_COLOR.get(card.grade, "#9e9e9e")
    score_pct = min(100, max(0, card.overall))
    avg_pos = f"{card.avg_position:.1f}" if card.avg_position else "–"
    mention_pct = f"{card.mention_rate * 100:.0f}%"

    model_rows = ""
    for m in card.per_model:
        if m.error:
            badge = '<span class="badge badge-err">Error</span>'
        elif m.position:
            badge = f'<span class="badge badge-rank">#{m.position}</span>'
        elif m.mentioned:
            badge = '<span class="badge badge-mention">Mentioned</span>'
        else:
            badge = '<span class="badge badge-miss">Not found</span>'
        comps = ", ".join(m.competitors[:3]) or "–"
        model_rows += f"""
<tr>
  <td>{m.model_label}</td>
  <td>{badge}</td>
  <td>{m.sentiment}</td>
  <td style="font-size:.82rem;color:#64748b">{comps}</td>
  <td>{m.error or ""}</td>
</tr>"""

    verif_rows = ""
    for v in card.verifications:
        mark = "✅" if v["found"] else "❌"
        link = (
            f'<a href="{v["top_hit_url"]}" target="_blank">{v["top_hit_title"]}</a>'
            if v["top_hit_url"] else "–"
        )
        verif_rows += f"<tr><td>{mark} {v['brand']}</td><td>{link}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEO Report — {card.target}</title>
<style>{_CSS}</style>
</head>
<body>

<div class="header">
  <h1>AEO Diagnostic Report</h1>
  <p class="meta">Query: <strong>"{card.query}"</strong> &nbsp;·&nbsp; Target: <strong>{card.target}</strong></p>
</div>

<div class="score-strip">
  <div class="grade-box" style="background:{grade_color}">
    <span class="letter">{card.grade}</span>
    <span class="lbl">AEO Grade</span>
  </div>
  <div class="score-detail">
    <h2>Overall AEO Score</h2>
    <span class="score-num" style="color:{grade_color}">{card.overall}</span>
    <span style="color:var(--muted)">/100</span>
    <div class="bar-wrap"><div class="bar-fill" style="width:{score_pct:.0f}%"></div></div>
    <div class="pills">
      <span class="pill pill-{'green' if card.mention_rate == 1 else 'amber' if card.mention_rate > 0 else 'red'}">
        Mentioned {mention_pct} of models
      </span>
      <span class="pill {'pill-green' if card.avg_position and card.avg_position <= 3 else 'pill-amber'}">
        Avg position {avg_pos}
      </span>
    </div>
  </div>
</div>

<section>
  <h2>Per-Model Breakdown</h2>
  <table class="comp-table">
    <thead><tr><th>Model</th><th>Rank</th><th>Sentiment</th><th>Top Competitors</th><th>Error</th></tr></thead>
    <tbody>{model_rows}</tbody>
  </table>
</section>

{"" if not verif_rows else f'''<section>
  <h2>Citation Verification ({card.citation_score:.0f}% found on web)</h2>
  <table class="comp-table">
    <thead><tr><th>Brand</th><th>Top Result</th></tr></thead>
    <tbody>{verif_rows}</tbody>
  </table>
</section>'''}

<footer>Generated by <strong>AEO Diagnostic</strong> &mdash; LangChain · LangGraph · DuckDuckGo</footer>
</body>
</html>"""
