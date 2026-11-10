"""Nightly export pipeline for the records desk.

The pipeline turns the audit tables into the CSV bundles that are handed to
the department reporting service. Each stage is anchored for the reference
index.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Iterable

LOG = logging.getLogger(__name__)

# ANCHOR-E01: CSV column ordering
COLUMNS = ["record_id", "record_class", "closed_on", "custodian", "status"]


def render_rows(rows: Iterable[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in COLUMNS})
    return buffer.getvalue()


# ANCHOR-E02: Delimiter normalisation
def normalise_delimiter(text: str) -> str:
    """Replace semicolon separated exports with commas."""
    return text.replace(";", ",")


# ANCHOR-E03: Omitted-fields monitor
def missing_fields(rows: Iterable[dict]) -> int:
    """Count rows that lack a custodian value."""
    return sum(1 for row in rows if not row.get("custodian"))


# ANCHOR-E04: Row-count reconciliation
def reconcile_row_counts(exported: int, expected: int) -> bool:
    """Compare the exported row count with the source table count."""
    return exported == expected
