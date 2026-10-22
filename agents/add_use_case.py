#!/usr/bin/env python3
"""
Add a use case config to use_cases/.

    python add_use_case.py --industry Legal \
        --use-case "E-Discovery & Case Preparation" \
        --description "Identify relevant documents and build coherent case arguments." \
        --profile analyst

Compliance standards default to the industry's list in neuron_agent.INDUSTRY_COMPLIANCE.
Prints the path of the new file. Refuses to overwrite an existing use case.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from neuron_agent import BEHAVIOR_PROFILES, INDUSTRY_COMPLIANCE, USE_CASES_DIR


def use_case_key(industry: str, use_case: str) -> str:
    text = f"{industry} {use_case}".lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--industry", required=True, choices=sorted(INDUSTRY_COMPLIANCE)
    )
    parser.add_argument(
        "--use-case",
        required=True,
        help="what the agent is for, e.g. 'Predictive Maintenance'",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="one sentence on what the use case delivers",
    )
    parser.add_argument(
        "--profile", default="balanced", choices=sorted(BEHAVIOR_PROFILES)
    )
    parser.add_argument(
        "--compliance", help="comma separated standards (default: the industry's list)"
    )
    args = parser.parse_args()

    use_case = args.use_case.strip()
    description = args.description.strip()
    if not use_case or not description:
        parser.error("--use-case and --description must not be empty")

    standards = (
        [s.strip() for s in args.compliance.split(",") if s.strip()]
        if args.compliance
        else INDUSTRY_COMPLIANCE[args.industry]
    )

    path = USE_CASES_DIR / f"{use_case_key(args.industry, use_case)}.json"
    if path.exists():
        sys.exit(f"{path.name} already exists")

    config = {
        "industry": args.industry,
        "use_case": use_case,
        "description": description,
        "behavior_profile": args.profile,
        "compliance_standards": standards,
    }
    path.write_text(json.dumps(config, indent=2) + "\n")
    print(path)


if __name__ == "__main__":
    main()
