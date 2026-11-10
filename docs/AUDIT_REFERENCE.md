# Records Desk Reference Index

This index points at the exact source lines where each documented rule is
defined. Entries use the form `path:line - description`. When a source file
is reorganised, only the line numbers change; descriptions and entry order
are stable.

## tools/retention_audit.py
- tools/retention_audit.py:33 - Default retention windows per record class
- tools/retention_audit.py:72 - Case-file purge eligibility check
- tools/retention_audit.py:101 - Legal-hold override handling
- tools/retention_audit.py:111 - Cross-border transfer flag
- tools/retention_audit.py:121 - Audit-trail checksum verification
- tools/retention_audit.py:130 - Disposal certificate generation
- tools/retention_audit.py:160 - Embargo expiry calculation
- tools/retention_audit.py:166 - Duplicate record detection
- tools/retention_audit.py:184 - Chain-of-custody reconciliation
- tools/retention_audit.py:191 - Redaction queue handoff
- tools/retention_audit.py:201 - Quarterly retention report export

## tools/export_pipeline.py
- tools/export_pipeline.py:17 - CSV column ordering
- tools/export_pipeline.py:30 - Delimiter normalisation
- tools/export_pipeline.py:36 - Omitted-fields monitor
- tools/export_pipeline.py:42 - Row-count reconciliation

## Conventions

- Never rewrite an entry description; only the trailing line number may change.
- Keep the entries in the order shown above.
- Add new sections at the bottom of the file.

## Intake workflow

Documents staged in `records/intake/` are filed into one of the existing
application-material folders under `records/`. Every staged document must
leave the intake folder with its original filename.
