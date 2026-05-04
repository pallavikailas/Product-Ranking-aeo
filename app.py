"""
Streamlit UI for the AEO Diagnostic tool.

Run: streamlit run app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

# Bridge Streamlit Cloud secrets → os.environ so all downstream code works
# unchanged whether running locally or on Streamlit Community Cloud.
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ.setdefault("GROQ_API_KEY", st.secrets["GROQ_API_KEY"])
except Exception:
    pass  # secrets.toml not present locally — fall back to env var

from src.clients import query_all
from src.scorer import score_panel
from src.report import write_reports


st.set_page_config(page_title="AEO Diagnostic", page_icon="🔍", layout="wide")

st.markdown(
    """
    <style>
      .grade-card {background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:24px;text-align:center;}
      .grade-letter {font-size:72px;font-weight:700;line-height:1;}
      .stat-card {background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;}
      .stat-k {color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.04em;}
      .stat-v {font-size:24px;font-weight:600;margin-top:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def grade_color(g: str) -> str:
    return {
        "A+": "#0d9b6c", "A": "#0d9b6c", "B": "#3b82f6",
        "C": "#f59e0b", "D": "#f97316", "F": "#dc2626",
    }.get(g, "#6b7280")


st.title("🔍 AEO Diagnostic")
st.caption(
    "How does your brand rank when shoppers ask AI? "
    "We send your query to a panel of 3 independent LLMs via **LangChain**, "
    "orchestrate scoring with **LangGraph**, and verify every citation against the open web."
)

with st.sidebar:
    st.header("Run a diagnostic")
    query = st.text_input(
        "Shopper query",
        value="best magnesium supplement for seniors",
        help="The actual question a shopper might ask an AI assistant.",
    )
    target = st.text_input("Your brand", value="Nature Made")
    verify = st.checkbox("Verify citations on the open web", value=True)
    deep = st.checkbox("Run deep agent analysis", value=False,
                       help="Uses a LangGraph ReAct agent for detailed recommendations.")
    run = st.button("Run diagnostic", type="primary", use_container_width=True)
    st.divider()
    st.caption(
        "Panel: Llama 3.3 70B · Mixtral 8x7B · Gemma 2 9B — via **Groq + LangChain**.  \n"
        "Pipeline: **LangGraph** state machine.  \n"
        "Citation verifier: DuckDuckGo."
    )
    if not os.environ.get("GROQ_API_KEY"):
        st.warning("GROQ_API_KEY env var is not set.")

if run:
    if not os.environ.get("GROQ_API_KEY"):
        st.error("Set GROQ_API_KEY before running. Get a free key at https://console.groq.com/keys")
        st.stop()

    progress = st.empty()
    with progress.container():
        with st.spinner("Querying Llama, Mixtral & Gemma via Groq + LangChain …"):
            responses = query_all(query)
        with st.spinner("Scoring, verifying citations, running LangGraph pipeline …"):
            card = score_panel(target, query, responses, verify_citations=verify)
            html_path, json_path = write_reports(card, Path("reports"))
    progress.empty()

    # ── Hero card ─────────────────────────────────────────────────────────────
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown(
            f"""<div class='grade-card'>
              <div class='grade-letter' style='color:{grade_color(card.grade)}'>{card.grade}</div>
              <div style='color:#64748b;margin-top:4px;'>{card.overall:.1f} / 100</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.subheader(card.target)
        st.write(f"Query: *{card.query}*")

    # ── Stats row ─────────────────────────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    avg_pos = f"{card.avg_position:.1f}" if card.avg_position is not None else "–"
    for col, k, v in [
        (s1, "Mention rate", f"{card.mention_rate * 100:.0f}%"),
        (s2, "Avg position", avg_pos),
        (s3, "Sentiment", f"{card.sentiment_score:.0f}"),
        (s4, "Citation grounding", f"{card.citation_score:.0f}%"),
    ]:
        with col:
            st.markdown(
                f"<div class='stat-card'><div class='stat-k'>{k}</div>"
                f"<div class='stat-v'>{v}</div></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Per-model breakdown ───────────────────────────────────────────────────
    st.subheader("How each model answered")
    rows = [
        {
            "Model": m.model_label,
            "Mentioned": "✅" if m.mentioned else "❌",
            "Position": m.position if m.position else "–",
            "Sentiment": m.sentiment,
            "Top competitors named": ", ".join(m.competitors[:3]) or "–",
            "Error": m.error or "",
        }
        for m in card.per_model
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # ── Citation verification ─────────────────────────────────────────────────
    st.subheader("Citation verification")
    if not card.verifications:
        st.info("No brands extracted to verify (or verification was skipped).")
    else:
        for v in card.verifications:
            mark = "✅" if v["found"] else "❌"
            line = f"{mark} **{v['brand']}**"
            if v["top_hit_url"]:
                line += f" — [{v['top_hit_title']}]({v['top_hit_url']})"
            st.markdown(line)

    # ── Deep agent analysis ───────────────────────────────────────────────────
    if deep:
        st.divider()
        st.subheader("Deep Agent Analysis (LangGraph ReAct)")
        with st.spinner("Running deep research agent …"):
            from src.agents import run_deep_analysis
            analysis = run_deep_analysis(target, query, card.avg_position)
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
