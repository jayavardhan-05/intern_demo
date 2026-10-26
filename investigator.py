"""Evidence-based investigator and incident detection rules for SignalTrace V2."""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from models import CaseResult, PaymentRecord, ShipmentRecord

VALID_ISSUES = {"DOUBLE_CHARGE", "PAYMENT_FAILURES", "SHIPPED_UNPAID", "OTHER"}


def check_double_charge(
    payments: List[PaymentRecord],
) -> Tuple[str, List[str]]:
    """
    Signal A - DOUBLE_CHARGE:
    Use accepted SUCCESS payments for the same order, sorted by (timestamp, payment_id).
    Detect two records that have the same amount_cents and different provider_ref values.
    Choose the earliest qualifying second payment, then pair it with the earliest preceding
    qualifying first payment. Evidence: both payment IDs in chronological order.
    """
    success_payments = [p for p in payments if p.status == "SUCCESS"]
    # Payments are already sorted by (timestamp, payment_id)

    for j in range(1, len(success_payments)):
        p2 = success_payments[j]
        for i in range(j):
            p1 = success_payments[i]
            if p1.amount_cents == p2.amount_cents and p1.provider_ref != p2.provider_ref:
                return "SIGNAL_FOUND", [p1.payment_id, p2.payment_id]

    return "NOT_VERIFIED", []


def check_payment_failures(
    payments: List[PaymentRecord],
) -> Tuple[str, List[str]]:
    """
    Signal B - PAYMENT_FAILURES:
    For a single order, sort only accepted FAILED payments by (timestamp, payment_id).
    Find the earliest three consecutive entries in that failed-payment sequence whose
    first-to-third interval is 10 minutes or less (inclusive, <= 600s).
    Evidence: those three payment IDs in that order.
    """
    failed_payments = [p for p in payments if p.status == "FAILED"]
    # Failed payments are already sorted by (timestamp, payment_id)

    if len(failed_payments) < 3:
        return "NOT_VERIFIED", []

    dts = [
        datetime.strptime(p.timestamp, "%Y-%m-%dT%H:%M:%SZ")
        for p in failed_payments
    ]

    for k in range(len(failed_payments) - 2):
        delta_sec = (dts[k + 2] - dts[k]).total_seconds()
        if delta_sec <= 600:
            return "SIGNAL_FOUND", [
                failed_payments[k].payment_id,
                failed_payments[k + 1].payment_id,
                failed_payments[k + 2].payment_id,
            ]

    return "NOT_VERIFIED", []


def check_shipped_unpaid(
    shipments: List[ShipmentRecord],
    payments: List[PaymentRecord],
) -> Tuple[str, List[str]]:
    """
    Signal C - SHIPPED_UNPAID:
    For a single order, sort accepted SHIPMENT_CREATED events by (timestamp, event_id).
    Find the earliest shipment event for which there is no SUCCESS payment with a
    strictly earlier timestamp. Evidence: that shipment event ID.
    """
    shipment_events = [s for s in shipments if s.event_type == "SHIPMENT_CREATED"]
    success_payments = [p for p in payments if p.status == "SUCCESS"]

    for s in shipment_events:
        has_earlier_success = any(p.timestamp < s.timestamp for p in success_payments)
        if not has_earlier_success:
            return "SIGNAL_FOUND", [s.event_id]

    return "NOT_VERIFIED", []


def evaluate_case(
    ticket_id: str,
    validated_order_id: Optional[str],
    validated_issue: str,
    known_orders: Set[str],
    order_payments_map: Dict[str, List[PaymentRecord]],
    order_shipments_map: Dict[str, List[ShipmentRecord]],
) -> CaseResult:
    """
    Determine the verdict and evidence based on the validated extraction and records.
    """
    if validated_issue == "OTHER":
        return CaseResult(
            ticket_id=ticket_id,
            order_id=validated_order_id,
            issue="OTHER",
            verdict="NOT_APPLICABLE",
            evidence_ids=[],
        )

    # Issue is one of DOUBLE_CHARGE, PAYMENT_FAILURES, SHIPPED_UNPAID
    if validated_order_id is None or validated_order_id not in known_orders:
        return CaseResult(
            ticket_id=ticket_id,
            order_id=validated_order_id,
            issue=validated_issue,
            verdict="INSUFFICIENT_DATA",
            evidence_ids=[],
        )

    order_payments = order_payments_map.get(validated_order_id, [])
    order_shipments = order_shipments_map.get(validated_order_id, [])

    if validated_issue == "DOUBLE_CHARGE":
        verdict, evidence_ids = check_double_charge(order_payments)
    elif validated_issue == "PAYMENT_FAILURES":
        verdict, evidence_ids = check_payment_failures(order_payments)
    elif validated_issue == "SHIPPED_UNPAID":
        verdict, evidence_ids = check_shipped_unpaid(order_shipments, order_payments)
    else:
        verdict, evidence_ids = "NOT_APPLICABLE", []

    return CaseResult(
        ticket_id=ticket_id,
        order_id=validated_order_id,
        issue=validated_issue,
        verdict=verdict,
        evidence_ids=evidence_ids,
    )
