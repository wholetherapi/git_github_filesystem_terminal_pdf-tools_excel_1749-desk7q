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

# ANCHOR-R09: Chain-of-custody reconciliation
def custody_gaps(expected_events: Iterable[str], observed_events: Iterable[str]) -> List[str]:
    """Return custodian handovers that were expected but never observed."""
    observed = set(observed_events)
    return [event for event in expected_events if event not in observed]


# ANCHOR-R10: Redaction queue handoff
def redaction_queue(paths: Iterable[str]) -> List[Dict[str, str]]:
    """Build the payload handed to the redaction team."""
    return [{"path": path, "status": "queued"} for path in paths]

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
