"""
Streamlit UI for the AEO Diagnostic tool.

Run: streamlit run app.py
"""

from __future__ import annotations

import os
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

# ── Model metadata ────────────────────────────────────────────────────────────

_LOGO_META     = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Meta_Platforms_Inc._logo.svg/200px-Meta_Platforms_Inc._logo.svg.png"
_LOGO_OPENAI   = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/OpenAI_Logo.svg/200px-OpenAI_Logo.svg.png"
_LOGO_MISTRAL  = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Mistral_AI_logo_%282025%29.svg/200px-Mistral_AI_logo_%282025%29.svg.png"
_LOGO_ALIBABA  = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Alibaba_Group_Logo.svg/200px-Alibaba_Group_Logo.svg.png"
_LOGO_DEEPSEEK = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/DeepSeek_logo.svg/200px-DeepSeek_logo.svg.png"

_MODEL_META: dict[str, dict] = {
    "Llama 3.3 70B":       {"company": "Meta",     "logo": _LOGO_META,     "badge": "badge-meta"},
    "GPT-OSS 120B":        {"company": "OpenAI",   "logo": _LOGO_OPENAI,   "badge": "badge-openai"},
    "Mistral Saba 24B":    {"company": "Mistral",  "logo": _LOGO_MISTRAL,  "badge": "badge-mistral"},
    "GPT-OSS 20B":         {"company": "OpenAI",   "logo": _LOGO_OPENAI,   "badge": "badge-openai"},
    "Qwen3 32B":           {"company": "Alibaba",  "logo": _LOGO_ALIBABA,  "badge": "badge-alibaba"},
    "DeepSeek R1 Distill": {"company": "DeepSeek", "logo": _LOGO_DEEPSEEK, "badge": "badge-deepseek"},
}

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  .grade-card   {background:#fff;border:1px solid #e2e8f0;border-radius:16px;
                 padding:24px;text-align:center;}
  .grade-letter {font-size:72px;font-weight:700;line-height:1;}
  .stat-card    {background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;}
  .stat-k       {color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.04em;}
  .stat-v       {font-size:24px;font-weight:600;margin-top:4px;}

  .model-table  {width:100%;border-collapse:collapse;font-size:14px;}
  .model-table th {text-transform:uppercase;font-size:11px;letter-spacing:.05em;
                   background:#f8fafc;color:#64748b;
                   border-bottom:2px solid #e2e8f0;padding:8px 12px;text-align:left;}
  .model-table td {padding:10px 12px;vertical-align:middle;
                   border-bottom:1px solid #f1f5f9;}
  .model-table tr:hover td {background:#f8fafc;}

  .company-logo {height:14px;max-width:56px;object-fit:contain;
                 vertical-align:middle;margin-right:6px;}

  .badge-meta     {background:#e8f0fd;color:#1877F2;border-radius:4px;
                   padding:2px 7px;font-size:11px;font-weight:600;}
  .badge-openai   {background:#e6f5f1;color:#10A37F;border-radius:4px;
                   padding:2px 7px;font-size:11px;font-weight:600;}
  .badge-mistral  {background:#fff4e6;color:#f97316;border-radius:4px;
                   padding:2px 7px;font-size:11px;font-weight:600;}
  .badge-alibaba  {background:#fff1e6;color:#FF6A00;border-radius:4px;
                   padding:2px 7px;font-size:11px;font-weight:600;}
  .badge-deepseek {background:#eff6ff;color:#2563eb;border-radius:4px;
                   padding:2px 7px;font-size:11px;font-weight:600;}
</style>
""", unsafe_allow_html=True)


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


# ── HTML model table ──────────────────────────────────────────────────────────

def _logo_html(label: str) -> str:
    m = _MODEL_META.get(label, {})
    url   = m.get("logo", "")
    company = m.get("company", "")
    badge = m.get("badge", "badge-meta")
    if url:
        return f'<img src="{url}" class="company-logo" alt="{company}" title="{company}">'
    return f'<span class="{badge}">{company}</span>'


def _model_table_html(per_model) -> str:
    rows = ""
    for m in per_model:
        err   = f'<br><span style="color:#f87171;font-size:12px">{m.error}</span>' if m.error else ""
        comps = ", ".join(m.competitors[:3]) or "–"
        rows += (
            f"<tr>"
            f"<td>{_logo_html(m.model_label)}</td>"
            f"<td><strong>{m.model_label}</strong>{err}</td>"
            f"<td style='text-align:center'>{'✅' if m.mentioned else '❌'}</td>"
            f"<td style='text-align:center'>{m.position or '–'}</td>"
            f"<td>{m.sentiment or '–'}</td>"
            f"<td style='color:#94a3b8;font-size:13px'>{comps}</td>"
            f"</tr>"
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
    query = st.text_input(
        "Shopper query", value="best magnesium supplement for seniors",
        help="The actual question a shopper might ask an AI assistant.",
    )
    target = st.text_input("Your brand", value="Nature Made")
    verify = st.checkbox("Verify citations on the open web", value=True)
    deep = st.checkbox(
        "Run deep agent analysis", value=False,
        help="LangGraph ReAct agent with temporal analysis.",
    )
    run = st.button("Run diagnostic", type="primary", use_container_width=True)
    st.divider()
    st.caption(
        "**LLM Panel (Groq):**  \n"
        "• Llama 3.3 70B *(Meta)*  \n"
        "• GPT-OSS 120B *(OpenAI)*  \n"
        "• Mistral Saba 24B *(Mistral)*  \n"
        "• GPT-OSS 20B *(OpenAI)*  \n"
        "• Qwen3 32B *(Alibaba)*  \n"
        "• DeepSeek R1 Distill *(DeepSeek)*  \n\n"
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
        with st.spinner("Querying 6 LLMs (Meta · OpenAI · Mistral · Alibaba · DeepSeek) via Groq + LangChain …"):
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

    # ── Stats row with colour grading ─────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    avg_pos = card.avg_position
    for col, k, v, color in [
        (s1, "Mention rate",       f"{card.mention_rate * 100:.0f}%",      mention_color(card.mention_rate)),
        (s2, "Avg position",       f"{avg_pos:.1f}" if avg_pos else "–",    position_color(avg_pos)),
        (s3, "Sentiment",          f"{card.sentiment_score:.0f}",           "#6b7280"),
        (s4, "Citation grounding", f"{card.citation_score:.0f}%",           "#6b7280"),
    ]:
        with col:
            st.markdown(
                f"<div class='stat-card'>"
                f"<div class='stat-k'>{k}</div>"
                f"<div class='stat-v' style='color:{color}'>{v}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Per-model breakdown with logos ────────────────────────────────────────
    st.subheader("How each model answered")
    st.markdown(_model_table_html(card.per_model), unsafe_allow_html=True)

    # ── Citation verification (deduplicated) ──────────────────────────────────
    st.subheader("Citation verification")
    if not card.verifications:
        st.info("No brands extracted to verify (or verification was skipped).")
    else:
        seen: set[str] = set()
        for v in card.verifications:
            key = v["brand"].lower().strip()
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
