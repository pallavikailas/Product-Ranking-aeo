"""
Streamlit UI for the AEO Diagnostic tool.

Run: streamlit run app.py
"""

from __future__ import annotations

import os
import unicodedata
from collections import Counter
from pathlib import Path

import streamlit as st

try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ.setdefault("GROQ_API_KEY", st.secrets["GROQ_API_KEY"])
except Exception:
    pass

from src.clients import query_all
from src.scorer import score_panel
from src.report import write_reports


st.set_page_config(page_title="AEO Diagnostic", page_icon="🔍", layout="wide")

# ── Model metadata (badge-only — no broken external images) ───────────────────

_MODEL_META: dict[str, dict] = {
    "Llama 3.3 70B":        {"company": "Meta",    "badge": "badge-meta"},
    "GPT-OSS 120B":         {"company": "OpenAI",  "badge": "badge-openai"},
    "Llama 4 Scout 17B":    {"company": "Meta",    "badge": "badge-meta"},
    "Compound":             {"company": "Groq",    "badge": "badge-groq"},
    "Qwen3 32B":            {"company": "Alibaba", "badge": "badge-alibaba"},
    "Llama 3.1 8B Instant": {"company": "Meta",    "badge": "badge-meta"},
}

# ── CSS (light / dark) ────────────────────────────────────────────────────────

_SHARED = """
  .grade-card   {border-radius:16px;padding:24px;text-align:center;}
  .grade-letter {font-size:72px;font-weight:700;line-height:1;}
  .stat-card    {border-radius:12px;padding:16px;}
  .stat-k       {font-size:12px;text-transform:uppercase;letter-spacing:.04em;}
  .stat-v       {font-size:24px;font-weight:600;margin-top:4px;}
  .model-table  {width:100%;border-collapse:collapse;font-size:14px;}
  .model-table th {text-transform:uppercase;font-size:11px;letter-spacing:.05em;
                   padding:8px 12px;text-align:left;}
  .model-table td {padding:10px 12px;vertical-align:middle;}
  .badge-meta    {background:#e8f0fd;color:#1877F2;border-radius:4px;
                  padding:2px 7px;font-size:11px;font-weight:600;}
  .badge-openai  {background:#e6f5f1;color:#10A37F;border-radius:4px;
                  padding:2px 7px;font-size:11px;font-weight:600;}
  .badge-alibaba {background:#fff1e6;color:#FF6A00;border-radius:4px;
                  padding:2px 7px;font-size:11px;font-weight:600;}
  .badge-groq    {background:#f0f0ff;color:#6366f1;border-radius:4px;
                  padding:2px 7px;font-size:11px;font-weight:600;}
"""

_LIGHT = f"""<style>{_SHARED}
  .grade-card  {{background:#fff;border:1px solid #e2e8f0;}}
  .stat-card   {{background:#fff;border:1px solid #e2e8f0;}}
  .stat-k      {{color:#64748b;}}
  .model-table th {{background:#f8fafc;color:#64748b;border-bottom:2px solid #e2e8f0;}}
  .model-table td {{border-bottom:1px solid #f1f5f9;}}
  .model-table tr:hover td {{background:#f8fafc;}}
  .comp-track  {{background:#e2e8f0;border-radius:4px;height:6px;}}
  .comp-name   {{color:#1e293b;font-size:14px;font-weight:500;}}
  .comp-count  {{color:#64748b;font-size:12px;}}
</style>"""

_DARK = f"""<style>{_SHARED}
  .stApp,.main .block-container{{background-color:#0f172a!important;color:#f8fafc!important;}}
  .stSidebar{{background-color:#1e293b!important;}}
  .grade-card  {{background:#1e293b;border:1px solid #334155;}}
  .stat-card   {{background:#1e293b;border:1px solid #334155;}}
  .stat-k      {{color:#94a3b8;}}
  .stat-v      {{color:#f8fafc;}}
  .model-table th {{background:#1e293b;color:#94a3b8;border-bottom:2px solid #334155;}}
  .model-table td {{border-bottom:1px solid #263045;color:#e2e8f0;}}
  .model-table tr:hover td {{background:#293548;}}
  .badge-meta    {{background:#1e3a5f;color:#60a5fa;}}
  .badge-openai  {{background:#14302a;color:#34d399;}}
  .badge-alibaba {{background:#2d1a0a;color:#fb923c;}}
  .badge-groq    {{background:#1e1b4b;color:#a5b4fc;}}
  .comp-track  {{background:#334155;border-radius:4px;height:6px;}}
  .comp-name   {{color:#e2e8f0;font-size:14px;font-weight:500;}}
  .comp-count  {{color:#94a3b8;font-size:12px;}}
  p,li,.stMarkdown{{color:#e2e8f0!important;}}
  h1,h2,h3,h4,h5,h6{{color:#f8fafc!important;}}
  .stTextInput>div>div>input,.stTextArea textarea{{
    background:#1e293b!important;color:#f8fafc!important;border-color:#334155!important;}}
</style>"""

# ── Apply theme ───────────────────────────────────────────────────────────────

dark = st.session_state.get("dark_mode", False)
st.markdown(_DARK if dark else _LIGHT, unsafe_allow_html=True)

# ── Colour helpers ────────────────────────────────────────────────────────────

def grade_color(g: str) -> str:
    return {"A+": "#0d9b6c", "A": "#0d9b6c", "B": "#3b82f6",
            "C": "#f59e0b",  "D": "#f97316", "F": "#dc2626"}.get(g, "#6b7280")

def mention_color(rate: float) -> str:
    if rate <= 0.5:  return "#dc2626"
    if rate <= 0.75: return "#f59e0b"
    return "#0d9b6c"

def position_color(pos) -> str:
    if pos is None: return "#dc2626"
    if pos <= 3:    return "#0d9b6c"
    if pos <= 6:    return "#f59e0b"
    return "#dc2626"

# ── HTML helpers ──────────────────────────────────────────────────────────────

def _badge(label: str) -> str:
    m = _MODEL_META.get(label, {"company": label[:3], "badge": "badge-meta"})
    return f'<span class="{m["badge"]}">{m["company"]}</span>'

def _model_table_html(per_model) -> str:
    rows = ""
    for m in per_model:
        err   = f'<br><span style="color:#f87171;font-size:12px">{m.error}</span>' if m.error else ""
        comps = ", ".join(m.competitors[:3]) or "–"
        rows += (
            f"<tr><td>{_badge(m.model_label)}</td>"
            f"<td><strong>{m.model_label}</strong>{err}</td>"
            f"<td style='text-align:center'>{'✅' if m.mentioned else '❌'}</td>"
            f"<td style='text-align:center'>{m.position or '–'}</td>"
            f"<td>{m.sentiment or '–'}</td>"
            f"<td style='color:#94a3b8;font-size:13px'>{comps}</td></tr>"
        )
    return (
        "<table class='model-table'><thead><tr>"
        "<th>Co.</th><th>Model</th>"
        "<th style='text-align:center'>Mentioned</th>"
        "<th style='text-align:center'>Position</th>"
        "<th>Sentiment</th><th>Top Competitors</th>"
        f"</tr></thead><tbody>{rows}</tbody></table><br>"
    )

# ── Page header ───────────────────────────────────────────────────────────────

st.title("🔍 AEO Diagnostic")
st.caption(
    "How does your brand rank when shoppers ask AI? "
    "We query a panel of **6 LLMs** via **LangChain**, "
    "orchestrate scoring with **LangGraph**, and verify every citation against the open web."
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Run a diagnostic")
    query  = st.text_input("Shopper query", value="best magnesium supplement for seniors",
                           help="The actual question a shopper might ask an AI assistant.")
    target = st.text_input("Your brand", value="Nature Made")
    verify = st.checkbox("Verify citations on the open web", value=True)
    deep   = st.checkbox("Run deep agent analysis", value=False,
                         help="LangGraph ReAct agent with temporal analysis.")
    run    = st.button("Run diagnostic", type="primary", use_container_width=True)
    st.divider()

    night = st.toggle("🌙 Night mode", value=dark)
    if night != dark:
        st.session_state.dark_mode = night
        st.rerun()

    st.divider()
    st.caption(
        "**LLM Panel (Groq):**  \n"
        "• Llama 3.3 70B *(Meta)*  \n"
        "• GPT-OSS 120B *(OpenAI)*  \n"
        "• Llama 4 Scout 17B *(Meta)*  \n"
        "• Compound *(Groq — live search)*  \n"
        "• Qwen3 32B *(Alibaba)*  \n"
        "• Llama 3.1 8B Instant *(Meta)*  \n\n"
        "Pipeline: **LangGraph** state machine.  \n"
        "Citations: DuckDuckGo verifier."
    )
    if not os.environ.get("GROQ_API_KEY"):
        st.warning("GROQ_API_KEY env var is not set.")

# ── Main run ──────────────────────────────────────────────────────────────────

if run:
    if not os.environ.get("GROQ_API_KEY"):
        st.error("Set GROQ_API_KEY before running. Get a free key at https://console.groq.com/keys")
        st.stop()

    progress = st.empty()
    with progress.container():
        with st.spinner("Querying 6 LLMs (Meta · OpenAI · Groq · Alibaba) via Groq + LangChain …"):
            responses = query_all(query)
        with st.spinner("Scoring, verifying citations, running LangGraph pipeline …"):
            card = score_panel(target, query, responses, verify_citations=verify)
            html_path, json_path = write_reports(card, Path("reports"))
    progress.empty()

    # ── Hero card ─────────────────────────────────────────────────────────────
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown(
            f"<div class='grade-card'>"
            f"<div class='grade-letter' style='color:{grade_color(card.grade)}'>{card.grade}</div>"
            f"<div style='color:#64748b;margin-top:4px;'>{card.overall:.1f} / 100</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.subheader(card.target)
        st.write(f"Query: *{card.query}*")

    # ── Stats row ─────────────────────────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    avg_pos = card.avg_position
    for col, k, v, color in [
        (s1, "Mention rate",       f"{card.mention_rate * 100:.0f}%",     mention_color(card.mention_rate)),
        (s2, "Avg position",       f"{avg_pos:.1f}" if avg_pos else "–",   position_color(avg_pos)),
        (s3, "Sentiment",          f"{card.sentiment_score:.0f}",          "#6b7280"),
        (s4, "Citation grounding", f"{card.citation_score:.0f}%",          "#6b7280"),
    ]:
        with col:
            st.markdown(
                f"<div class='stat-card'><div class='stat-k'>{k}</div>"
                f"<div class='stat-v' style='color:{color}'>{v}</div></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Per-model breakdown ────────────────────────────────────────────────────
    st.subheader("How each model answered")
    st.markdown(_model_table_html(card.per_model), unsafe_allow_html=True)

    # ── Competitor landscape ──────────────────────────────────────────────────
    st.subheader("Competitor Landscape")
    st.caption("Brands recommended most consistently across all models — a proxy for AEO authority in this category")

    active = [pm for pm in card.per_model if not pm.error]
    n_total = len(card.per_model)
    comp_counts: Counter = Counter()
    for pm in active:
        seen_this_model: set[str] = set()
        for c in pm.competitors:
            c_norm = c.strip("®™ ").strip()
            if c_norm and target.lower() not in c_norm.lower() and c_norm.lower() not in seen_this_model:
                comp_counts[c_norm] += 1
                seen_this_model.add(c_norm.lower())

    if comp_counts:
        for brand, count in comp_counts.most_common(8):
            pct = count / n_total * 100
            bar_col = "#0d9b6c" if pct >= 60 else "#3b82f6" if pct >= 30 else "#94a3b8"
            st.markdown(
                f"<div style='margin-bottom:10px'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:3px'>"
                f"<span class='comp-name'>{brand}</span>"
                f"<span class='comp-count'>{count}/{n_total} models</span></div>"
                f"<div class='comp-track'>"
                f"<div style='background:{bar_col};width:{pct:.0f}%;height:6px;border-radius:4px'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No competitor data extracted.")

    st.divider()

    # ── Citation verification (deduplicated) ──────────────────────────────────
    st.subheader("Citation verification")
    if not card.verifications:
        st.info("No brands extracted to verify (or verification was skipped).")
    else:
        def _cite_key(s: str) -> str:
            # NFKD decomposition + drop non-ASCII → collapses all apostrophe/quote
            # variants, diacritics, and other Unicode punctuation differences
            nfkd = unicodedata.normalize("NFKD", s)
            return nfkd.encode("ascii", "ignore").decode().casefold().strip()

        seen: set[str] = set()
        for v in card.verifications:
            key = _cite_key(v["brand"])
            if key in seen:
                continue
            seen.add(key)
            mark = "✅" if v["found"] else "❌"
            line = f"{mark} **{v['brand']}**"
            if v["top_hit_url"]:
                line += f" — [{v['top_hit_title']}]({v['top_hit_url']})"
            st.markdown(line)

    # ── Deep agent analysis ───────────────────────────────────────────────────
    if deep:
        st.divider()
        st.subheader("Deep Agent Analysis (LangGraph ReAct)")
        st.caption(
            "Temporal analysis compares model knowledge cutoffs. "
            "Divergence reveals whether recent AEO strategy changes are working."
        )
        with st.spinner("Running deep research agent …"):
            from src.agents import run_deep_analysis
            analysis = run_deep_analysis(target, query, card.avg_position, card.per_model)
        st.markdown(analysis)

    # ── Raw model responses ───────────────────────────────────────────────────
    with st.expander("Raw model responses"):
        for r in responses:
            st.markdown(f"**{r.model_label}** · {r.latency_ms} ms")
            if r.error:
                st.error(r.error)
            else:
                st.code(r.text, language="markdown")

    st.divider()
    st.success(f"Reports saved: `{html_path}` and `{json_path}`")
    with open(html_path, "rb") as f:
        st.download_button("Download HTML report", f, file_name=html_path.name, mime="text/html")
    with open(json_path, "rb") as f:
        st.download_button("Download JSON report", f, file_name=json_path.name, mime="application/json")
