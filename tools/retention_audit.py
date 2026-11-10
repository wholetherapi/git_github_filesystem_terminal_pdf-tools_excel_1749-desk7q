"""Retention audit helpers for the department records desk.

This module implements the retention and disposal rules exercised during the
quarterly records review. Each rule carries an ``ANCHOR-*`` comment so that
``docs/AUDIT_REFERENCE.md`` can cite the exact line where the rule lives.

When this file is reorganised, update the line numbers in the index; the
descriptions and their order never change.
"""

from __future__ import annotations

import hashlib
import itertools
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, Iterator, List, Tuple

LOG = logging.getLogger(__name__)

# Desk-wide automation settings
AUDIT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
AUDIT_RUN_TAG = "records-desk"
EXPORT_ROOT = "exports"
MAX_BATCH = 200


def configure_audit_logging() -> None:
    """Apply the desk wide logging configuration."""
    logging.basicConfig(format=AUDIT_LOG_FORMAT, level=logging.INFO)

# ANCHOR-R01: Default retention windows per record class
DEFAULT_WINDOWS = {
    "case-file": 84,
    "correspondence": 60,
    "financial": 120,
    "personnel": 96,
    "facilities": 36,
}


def window_for(record_class: str) -> int:
    """Return the configured retention window in months."""
    return DEFAULT_WINDOWS.get(record_class, 24)

def fiscal_quarter_start(reference: date) -> date:
    """Return the first day of the fiscal quarter containing *reference*."""
    month = ((reference.month - 1) // 3) * 3 + 1
    return date(reference.year, month, 1)


def quarters_between(start: date, end: date) -> int:
    """Count complete fiscal quarters between two dates."""
    elapsed = (end.year - start.year) * 12 + (end.month - start.month)
    return elapsed // 3


def is_quarter_end(reference: date) -> bool:
    """Return True on the last day of a fiscal quarter."""
    return reference.month in (3, 6, 9, 12) and reference.day >= 28

@dataclass(frozen=True)
class RecordClass:
    """Description of a retained record family."""

    name: str
    window_months: int
    requires_certificate: bool = False


# ANCHOR-R02: Case-file purge eligibility check
def purge_eligible(closed_on: date, as_of: date, record_class: str = "case-file") -> bool:
    """Return True when a closed case may be purged."""
    if under_legal_hold((record_class,)):
        return False
    window = window_for(record_class)
    return closed_on + timedelta(days=30 * window) <= as_of

def classify_record(path: str) -> RecordClass:
    """Map a storage path to one of the configured record classes."""
    lowered = path.lower()
    if "correspondence" in lowered or "/mail/" in lowered:
        return RecordClass("correspondence", window_for("correspondence"))
    if "/finance/" in lowered or "invoice" in lowered:
        return RecordClass("financial", window_for("financial"), True)
    if "/hr/" in lowered or "personnel" in lowered:
        return RecordClass("personnel", window_for("personnel"))
    if "/facilities/" in lowered:
        return RecordClass("facilities", window_for("facilities"))
    return RecordClass("case-file", window_for("case-file"), True)


def grouped_by_class(paths: Iterable[str]) -> Dict[str, List[str]]:
    """Group storage paths by their record class."""
    groups: Dict[str, List[str]] = {}
    for path in paths:
        groups.setdefault(classify_record(path).name, []).append(path)
    return groups

# ANCHOR-R03: Legal-hold override handling
LEGAL_HOLD_MARKERS = ("litigation", "subpoena", "regulator-request")


def under_legal_hold(tags: Iterable[str]) -> bool:
    """Return True when any tag marks the record as under legal hold."""
    lowered = {tag.lower() for tag in tags}
    return any(marker in lowered for marker in LEGAL_HOLD_MARKERS)


# ANCHOR-R04: Cross-border transfer flag
def requires_transfer_review(destination_country: str, home_country: str = "NL") -> bool:
    """Cross-border copies need a review when the destination differs."""
    return destination_country.upper() != home_country.upper()

def hold_reason(tags: Iterable[str]) -> str:
    """Human readable reason for a legal hold, used in the audit narrative."""
    matches = sorted(tag for tag in tags if tag.lower() in LEGAL_HOLD_MARKERS)
    return ", ".join(matches) if matches else "none"

# ANCHOR-R05: Audit-trail checksum verification
def verify_audit_trail(chunks: Iterable[bytes], expected_digest: str) -> bool:
    """Recompute the audit trail digest and compare it with the recorded value."""
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk)
    return digest.hexdigest() == expected_digest


# ANCHOR-R06: Disposal certificate generation
def disposal_certificate(record_ids: Iterable[str], approved_on: date, approver: str) -> str:
    """Render the certificate that must accompany a disposal batch."""
    ids = ", ".join(sorted(record_ids))
    return (
        f"Disposal certificate\n"
        f"Approved on: {approved_on.isoformat()}\n"
        f"Approved by: {approver}\n"
        f"Records: {ids}\n"
    )

def retention_summary(records: Iterable[RecordClass]) -> Dict[str, int]:
    """Aggregate record classes for the quarterly dashboard."""
    summary: Dict[str, int] = {}
    for record in records:
        summary[record.name] = summary.get(record.name, 0) + 1
    return dict(sorted(summary.items()))


def batch_chunks(records: Iterable[str], size: int = 50) -> Iterator[List[str]]:
    """Yield fixed size batches so that disposal runs stay small."""
    buffer: List[str] = []
    for record in records:
        buffer.append(record)
        if len(buffer) == size:
            yield buffer
            buffer = []
    if buffer:
        yield buffer

# ANCHOR-R07: Embargo expiry calculation
def embargo_expired(embargo_until: date, as_of: date) -> bool:
    """Return True once the embargo date has passed."""
    return embargo_until < as_of


# ANCHOR-R08: Duplicate record detection
def duplicate_keys(record_ids: Iterable[str]) -> set[str]:
    """Return record identifiers that appear more than once."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record_id in record_ids:
        if record_id in seen:
            duplicates.add(record_id)
        seen.add(record_id)
    return duplicates

def next_review_window(as_of: date) -> Tuple[date, date]:
    """Return the fiscal quarter that follows *as_of*."""
    start = fiscal_quarter_start(as_of)
    advancing = 3 if start.month <= 9 else -9
    following = date(start.year + (1 if start.month == 10 else 0), start.month + advancing, 1)
    return start, following

# ANCHOR-R09: Chain-of-custody reconciliation
def custody_gaps(expected_events: Iterable[str], observed_events: Iterable[str]) -> List[str]:
    """Return custodian handovers that were expected but never observed."""
    observed = set(observed_events)
    return [event for event in expected_events if event not in observed]


# ANCHOR-R10: Redaction queue handoff
def redaction_queue(paths: Iterable[str]) -> List[Dict[str, str]]:
    """Build the payload handed to the redaction team."""
    return [{"path": path, "status": "queued"} for path in paths]

def audit_signature(actor: str, action: str, payload: str) -> str:
    """Produce a short signature used in the audit narrative."""
    raw = f"{actor}|{action}|{payload}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

# ANCHOR-R11: Quarterly retention report export
def export_report(rows: Iterable[Dict[str, object]], as_of: date) -> str:
    """Render the quarterly retention report as CSV text."""
    header = "record_class,window_months,requires_certificate"
    lines = [header]
    for row in rows:
        lines.append(f"{row['name']},{row['window_months']},{row['requires_certificate']}")
    return "\n".join(lines) + f"\nReport generated for {as_of.isoformat()}\n"


if __name__ == "__main__":
    LOG.info("Retention audit module loaded")
