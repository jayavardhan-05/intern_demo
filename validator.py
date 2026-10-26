"""Input parsing and validation for SignalTrace V2."""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

from models import ComplaintRecord, PaymentRecord, ShipmentRecord

UTC_TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def validate_utc_timestamp(ts: str) -> bool:
    """Validate that timestamp strictly matches YYYY-MM-DDTHH:MM:SSZ and is a real date/time."""
    if not isinstance(ts, str) or not UTC_TIMESTAMP_REGEX.match(ts):
        return False
    try:
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def load_payments(path: str) -> Tuple[Dict[str, int], List[PaymentRecord]]:
    """
    Load and validate payments CSV.
    Returns (stats_dict, accepted_records_list).
    """
    total = 0
    accepted = 0
    invalid = 0
    duplicates = 0
    seen_ids = set()
    records: List[PaymentRecord] = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            raw_header = next(reader)
        except StopIteration:
            return {"total": 0, "accepted": 0, "invalid": 0, "duplicates": 0}, []

        header = [col.strip() for col in raw_header]
        col_map = {col: idx for idx, col in enumerate(header)}
        required_cols = ["payment_id", "order_id", "timestamp", "status", "amount_cents"]

        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue

            total += 1

            # Check that required columns exist in row and are non-empty
            missing_or_empty = False
            for col in required_cols:
                if col not in col_map or col_map[col] >= len(row) or not row[col_map[col]].strip():
                    missing_or_empty = True
                    break

            if missing_or_empty:
                invalid += 1
                continue

            pid = row[col_map["payment_id"]].strip()
            oid = row[col_map["order_id"]].strip()
            ts = row[col_map["timestamp"]].strip()
            status = row[col_map["status"]].strip()
            amt_str = row[col_map["amount_cents"]].strip()
            pref = ""
            if "provider_ref" in col_map and col_map["provider_ref"] < len(row):
                pref = row[col_map["provider_ref"]].strip()

            # Validate fields
            is_valid = True
            if not validate_utc_timestamp(ts):
                is_valid = False
            elif status not in ("SUCCESS", "FAILED", "PENDING"):
                is_valid = False
            else:
                try:
                    amt = int(amt_str)
                    if amt <= 0 or not amt_str.isdigit():
                        is_valid = False
                except ValueError:
                    is_valid = False

            if is_valid and status == "SUCCESS" and not pref:
                is_valid = False

            if not is_valid:
                invalid += 1
                continue

            # Deduplication: an invalid row must not reserve an ID
            if pid in seen_ids:
                duplicates += 1
            else:
                seen_ids.add(pid)
                accepted += 1
                records.append(
                    PaymentRecord(
                        payment_id=pid,
                        order_id=oid,
                        timestamp=ts,
                        status=status,
                        amount_cents=int(amt_str),
                        provider_ref=pref,
                    )
                )

    stats = {
        "total": total,
        "accepted": accepted,
        "invalid": invalid,
        "duplicates": duplicates,
    }
    return stats, records


def load_shipments(path: str) -> Tuple[Dict[str, int], List[ShipmentRecord]]:
    """
    Load and validate shipments JSONL.
    Returns (stats_dict, accepted_records_list).
    """
    total = 0
    accepted = 0
    invalid = 0
    duplicates = 0
    seen_ids = set()
    records: List[ShipmentRecord] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue

            total += 1

            try:
                obj = json.loads(line_str)
            except Exception:
                invalid += 1
                continue

            if not isinstance(obj, dict):
                invalid += 1
                continue

            eid = obj.get("event_id")
            oid = obj.get("order_id")
            ts = obj.get("timestamp")
            etype = obj.get("event_type")

            if not (
                isinstance(eid, str)
                and eid.strip()
                and isinstance(oid, str)
                and oid.strip()
                and isinstance(ts, str)
                and validate_utc_timestamp(ts.strip())
                and isinstance(etype, str)
                and etype.strip()
            ):
                invalid += 1
                continue

            eid_clean = eid.strip()
            if eid_clean in seen_ids:
                duplicates += 1
            else:
                seen_ids.add(eid_clean)
                accepted += 1
                records.append(
                    ShipmentRecord(
                        event_id=eid_clean,
                        order_id=oid.strip(),
                        timestamp=ts.strip(),
                        event_type=etype.strip(),
                        details=obj.get("details"),
                    )
                )

    stats = {
        "total": total,
        "accepted": accepted,
        "invalid": invalid,
        "duplicates": duplicates,
    }
    return stats, records


def load_complaints(path: str) -> Tuple[Dict[str, int], List[ComplaintRecord]]:
    """
    Load and validate complaints JSONL.
    Returns (stats_dict, accepted_records_list).
    """
    total = 0
    accepted = 0
    invalid = 0
    duplicates = 0
    seen_ids = set()
    records: List[ComplaintRecord] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue

            total += 1

            try:
                obj = json.loads(line_str)
            except Exception:
                invalid += 1
                continue

            if not isinstance(obj, dict):
                invalid += 1
                continue

            tid = obj.get("ticket_id")
            msg = obj.get("message")

            if not (
                isinstance(tid, str)
                and tid.strip()
                and isinstance(msg, str)
                and msg.strip()
            ):
                invalid += 1
                continue

            tid_clean = tid.strip()
            if tid_clean in seen_ids:
                duplicates += 1
            else:
                seen_ids.add(tid_clean)
                accepted += 1
                records.append(
                    ComplaintRecord(
                        ticket_id=tid_clean,
                        message=msg,
                    )
                )

    stats = {
        "total": total,
        "accepted": accepted,
        "invalid": invalid,
        "duplicates": duplicates,
    }
    return stats, records
