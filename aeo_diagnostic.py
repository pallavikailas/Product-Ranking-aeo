#!/usr/bin/env python3
"""
AEO Diagnostic CLI
------------------
Queries GPT-4o, Claude Sonnet, and Gemini 1.5 Pro with the same product search
query and produces an HTML + JSON report card showing how a target brand ranks
versus its competitors across all three AI answer engines.

Usage
-----
    python aeo_diagnostic.py \
        --query "best magnesium supplement for seniors" \
        --brand "Nature Made" \
        --output-dir reports/

Required environment variables (set as GitHub Actions secrets or in .env):
    OPENAI_API_KEY
    ANTHROPIC_API_KEY
    GEMINI_API_KEY
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys

from src.clients import ALL_CLIENTS
from src.models import AEOReport
from src.parser import process_result
from src.report import save_html, save_json
from src.scoring import aggregate_competitors, overall_score_and_grade


def run_diagnostic(query: str, target_brand: str) -> AEOReport:
    print(f"\n{'='*60}")
    print(f"  AEO Diagnostic")
    print(f"  Query : {query}")
    print(f"  Target: {target_brand}")
    print(f"{'='*60}\n")

    results = []
    for client_fn in ALL_CLIENTS:
        # Each client function name tells us which model we're calling
        label = client_fn.__name__.replace("query_", "").replace("_", " ").title()
        print(f"  → Querying {label} … ", end="", flush=True)
        result = process_result(client_fn(query), target_brand)
        status = "✓" if not result.error else f"✗  {result.error}"
        print(status)
        results.append(result)

    overall_score, grade = overall_score_and_grade(results)
    competitors = aggregate_competitors(results, target_brand)

    print(f"\n  Score : {overall_score}/100   Grade : {grade}\n")

    return AEOReport(
        query=query,
        target_brand=target_brand,
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        results=results,
        competitors=competitors,
        overall_score=overall_score,
        grade=grade,
    )


def _output_paths(output_dir: str, brand: str) -> tuple[str, str]:
    slug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")
    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.join(output_dir, f"aeo_{slug}_{date_str}")
    return base + ".html", base + ".json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AEO Diagnostic — rank your brand across AI answer engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--query", required=True,
        help='Product search query, e.g. "best magnesium supplement for seniors"',
    )
    parser.add_argument(
        "--brand", required=True,
        help="Target brand to track (e.g. 'Nature Made')",
    )
    parser.add_argument(
        "--output-dir", default="reports",
        help="Directory for output files (default: reports/)",
    )
    args = parser.parse_args()

    report = run_diagnostic(args.query, args.brand)

    html_path, json_path = _output_paths(args.output_dir, args.brand)
    print("Saving reports …")
    save_html(report, args.brand.lower(), html_path)
    save_json(report, json_path)

    print(f"\nDone.  Open {html_path} in a browser to view the report card.")
    sys.exit(0 if report.grade not in ("F", "N/A") else 1)


if __name__ == "__main__":
    main()
