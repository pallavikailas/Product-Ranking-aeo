#!/usr/bin/env python3
"""
AEO Diagnostic CLI — powered by LangChain + LangGraph
------------------------------------------------------
Queries GPT-4o, Claude Sonnet, and Gemini 1.5 Pro with the same product search
query via LangChain chains, orchestrates the pipeline with LangGraph, and
produces an HTML + JSON report card showing how a target brand ranks versus
competitors across all three AI answer engines.

Usage
-----
    python aeo_diagnostic.py \\
        --query "best magnesium supplement for seniors" \\
        --target "Nature Made"

    # Also run the LangGraph deep-agent analysis:
    python aeo_diagnostic.py \\
        --query "best magnesium supplement for seniors" \\
        --target "Nature Made" \\
        --deep-analysis

    # Skip DuckDuckGo citation verification:
    python aeo_diagnostic.py --query "..." --target "..." --no-verify

Required environment variables (set as GitHub Actions secrets or in .env):
    OPENAI_API_KEY
    ANTHROPIC_API_KEY
    GEMINI_API_KEY
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.clients import query_all
from src.scorer import score_panel
from src.report import write_reports


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AEO Diagnostic — rank your brand across AI answer engines (LangChain + LangGraph)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--query", required=True,
        help='Product search query, e.g. "best magnesium supplement for seniors"',
    )
    parser.add_argument(
        "--target", required=True,
        help="Target brand to track (e.g. 'Nature Made')",
    )
    parser.add_argument(
        "--no-verify", action="store_true",
        help="Skip DuckDuckGo citation verification",
    )
    parser.add_argument(
        "--deep-analysis", action="store_true",
        help="Run the LangGraph ReAct agent for deeper brand insights",
    )
    parser.add_argument(
        "--output-dir", default="reports",
        help="Directory for output files (default: reports/)",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  AEO Diagnostic  (LangChain · LangGraph · Deep Agents)")
    print(f"  Query : {args.query}")
    print(f"  Target: {args.target}")
    print(f"{'='*60}\n")

    # ── 1. Query the LLM panel via LangChain chains ───────────────────────────
    responses = query_all(args.query)

    # ── 2. Score and verify via scorer (uses web_verifier + parser) ──────────
    print("\nScoring & verifying …")
    card = score_panel(
        args.target, args.query, responses,
        verify_citations=not args.no_verify,
    )

    print(f"\n  Overall  : {card.overall}/100   Grade : {card.grade}")
    print(f"  Mention  : {card.mention_rate * 100:.0f}% of models")
    if card.avg_position is not None:
        print(f"  Avg pos  : {card.avg_position:.1f}")
    print(f"  Sentiment: {card.sentiment_score:.0f}")
    print(f"  Citation : {card.citation_score:.0f}%")

    # ── 3. Optional deep-agent analysis ──────────────────────────────────────
    if args.deep_analysis:
        print("\nRunning deep agent analysis (LangGraph ReAct) …")
        from src.agents import run_deep_analysis
        analysis = run_deep_analysis(args.target, args.query, card.avg_position)
        print(f"\n{analysis}\n")

    # ── 4. Save reports ───────────────────────────────────────────────────────
    print("\nSaving reports …")
    html_path, json_path = write_reports(card, Path(args.output_dir))
    print(f"  HTML → {html_path}")
    print(f"  JSON → {json_path}")
    print(f"\nDone.  Open {html_path} in a browser to view the report card.")

    sys.exit(0 if card.grade not in ("F", "N/A") else 1)


if __name__ == "__main__":
    main()
