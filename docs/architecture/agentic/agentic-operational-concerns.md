# Agentic Operational Concerns

## Status
Draft

## Purpose
Define persistence services, backup/restore considerations, and security/redaction roadmap.

## Scope
Local dev vs. service deployments, backup and restore behavior, and planned hardening.

## Contents

### Persistence Services
CHAOS uses two separate persistence services.

- Raw Memory DB (authoritative, text + metadata):
  - Local dev default: `.chaos/db/raw.sqlite`.
  - Production target: dedicated DB service (Docker container), suitable for concurrency (e.g., Postgres).
  - Transactions: idetic write + LTM insert should be in a single transaction when possible.
  - Concurrency: prefer many readers and moderate writers; heavy concurrent writes use batching or a single-writer queue.

- Vector Store (embeddings only):
  - Local dev default: `.chaos/db/chroma/`.
  - Production target: dedicated vector service (Docker container).
  - Upserts must be idempotent on `ltm_entries.id`.

Backup and restore:
- Backup `.chaos/identities/`, raw memory DB, and vector store persistence.
- Restore must keep raw DB ids stable to preserve vector id mapping.

### Security and Redaction Roadmap
Current posture (explicitly temporary):
- All tool inputs/outputs and messages are logged to idetic memory.

Planned hardening:
- Redaction policy at ingestion for known secret patterns and high-risk tool outputs.
- Optional encryption at rest for raw memory DB.
- Metadata tagging for sensitive events (`metadata.sensitivity`).
- Retrieval-time safety filters to prevent sensitive tool output from appearing in Actor prompts.

## References
- [Agentic Architecture Index](index.md)
- [Architecture Index](../index.md)
