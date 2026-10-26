"""SignalTrace V2 — Main Application Entry Point."""

import argparse
import collections
import json
import os
import sys

from extractor import extract_with_llm, load_offline_extractions, validate_extraction
from investigator import evaluate_case
from models import CaseResult
from validator import load_complaints, load_payments, load_shipments


def parse_args():
    parser = argparse.ArgumentParser(
        description="SignalTrace V2: Evidence-Driven AI Investigator"
    )
    parser.add_argument(
        "--payments",
        required=True,
        help="Path to payments.csv",
    )
    parser.add_argument(
        "--shipments",
        required=True,
        help="Path to shipments.jsonl",
    )
    parser.add_argument(
        "--complaints",
        required=True,
        help="Path to complaints.jsonl",
    )
    parser.add_argument(
        "--extractions",
        default=None,
        help="Path to extractions.json (offline fixture mode)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write output JSON",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "gemini"],
        default=None,
        help="LLM inference provider for live mode (default: auto-detect)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name for live LLM mode",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional API key override",
    )
    return parser.parse_args()


def run_pipeline(args):
    # 1. Ingest and validate all sources
    payments_stats, accepted_payments = load_payments(args.payments)
    shipments_stats, accepted_shipments = load_shipments(args.shipments)
    complaints_stats, accepted_complaints = load_complaints(args.complaints)

    # 2. Sort accepted records according to specification
    # Payments: sorted by (timestamp, payment_id)
    accepted_payments.sort(key=lambda p: (p.timestamp, p.payment_id))
    # Shipments: sorted by (timestamp, event_id)
    accepted_shipments.sort(key=lambda s: (s.timestamp, s.event_id))

    # 3. Build lookup indexes
    known_orders = {p.order_id for p in accepted_payments} | {
        s.order_id for s in accepted_shipments
    }

    order_payments_map = collections.defaultdict(list)
    for p in accepted_payments:
        order_payments_map[p.order_id].append(p)

    order_shipments_map = collections.defaultdict(list)
    for s in accepted_shipments:
        order_shipments_map[s.order_id].append(s)

    # 4. Extract and investigate complaints
    llm_errors = 0
    cases = []

    if args.extractions:
        # Offline mode: read extractions JSON fixture, zero network calls, llm_errors must be 0
        offline_extractions = load_offline_extractions(args.extractions)
        for comp in accepted_complaints:
            ext = offline_extractions.get(comp.ticket_id)
            raw_order_id = ext.get("order_id") if ext else None
            raw_issue = ext.get("issue") if ext else None

            val_order_id, val_issue = validate_extraction(
                raw_order_id, raw_issue, comp.message
            )
            case = evaluate_case(
                ticket_id=comp.ticket_id,
                validated_order_id=val_order_id,
                validated_issue=val_issue,
                known_orders=known_orders,
                order_payments_map=order_payments_map,
                order_shipments_map=order_shipments_map,
            )
            cases.append(case)
    else:
        # Live LLM inference mode
        for comp in accepted_complaints:
            raw_ext = extract_with_llm(
                comp.message,
                provider=args.provider,
                model=args.model,
                api_key=args.api_key,
            )
            if raw_ext is None:
                llm_errors += 1
                case = CaseResult(
                    ticket_id=comp.ticket_id,
                    order_id=None,
                    issue="OTHER",
                    verdict="NOT_APPLICABLE",
                    evidence_ids=[],
                )
                cases.append(case)
            else:
                raw_order_id = raw_ext.get("order_id")
                raw_issue = raw_ext.get("issue")

                val_order_id, val_issue = validate_extraction(
                    raw_order_id, raw_issue, comp.message
                )
                case = evaluate_case(
                    ticket_id=comp.ticket_id,
                    validated_order_id=val_order_id,
                    validated_issue=val_issue,
                    known_orders=known_orders,
                    order_payments_map=order_payments_map,
                    order_shipments_map=order_shipments_map,
                )
                cases.append(case)

    # 5. Cases must be sorted lexicographically by ticket_id
    cases.sort(key=lambda c: c.ticket_id)

    # 6. Build final output document
    result = {
        "stats": {
            "payments": payments_stats,
            "shipments": shipments_stats,
            "complaints": complaints_stats,
            "llm_errors": llm_errors,
        },
        "cases": [case.to_dict() for case in cases],
    }

    # Ensure parent output directory exists if specified
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Investigation complete. Result written to {args.output}")


def main():
    args = parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
