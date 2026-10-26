"""Data models for SignalTrace V2."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PaymentRecord:
    payment_id: str
    order_id: str
    timestamp: str
    status: str
    amount_cents: int
    provider_ref: str


@dataclass
class ShipmentRecord:
    event_id: str
    order_id: str
    timestamp: str
    event_type: str
    details: Optional[str] = None


@dataclass
class ComplaintRecord:
    ticket_id: str
    message: str


@dataclass
class CaseResult:
    ticket_id: str
    order_id: Optional[str]
    issue: str
    verdict: str
    evidence_ids: List[str]

    def to_dict(self):
        return {
            "ticket_id": self.ticket_id,
            "order_id": self.order_id,
            "issue": self.issue,
            "verdict": self.verdict,
            "evidence_ids": self.evidence_ids,
        }
