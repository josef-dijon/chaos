# Agentic Migration and Versioning

## Status
Draft

## Purpose
Define identity and storage migration requirements and versioning policy.

## Scope
Identity schema versioning, raw DB schema versioning, and vector store rebuild policy.

## Contents

### Migration Policy
- Identity must include `schema_version`.
- Raw DB schema must include a `schema_meta` record for schema version.
- Migrations must be explicit, forward-only, and tested.

### Migration Types
- Identity migrations: transform JSON to the newest schema.
- Raw DB migrations: apply SQL migrations.
- Vector store migrations: rebuild from `ltm_entries` when necessary.

## References
- [Agentic Architecture Index](index.md)
- [Architecture Index](../index.md)
