# Agentic Memory Storage Layout

## Status
Draft

## Purpose
Specify the storage layout for raw memory, vector storage, and identity persistence.

## Scope
CHAOS_HOME layout, raw DB schema, and vector store contract.

## Contents

### Storage Layout (Global Raw DB + Separate Vector Store)
CHAOS separates raw text persistence from vector retrieval.

CHAOS_HOME (project-local): All CHAOS artifacts live under `.chaos/` in the current project directory. No CHAOS-managed state may be created in the project root.

Canonical local-dev layout:

```text
.chaos/
  identities/
    <agent_id>.identity.json
  db/
    raw.sqlite
    chroma/
```

#### Identity (Local Dev)
- Filesystem is the current source of truth for identity.
- Identity files are stored under `.chaos/identities/`.
- Identity may be mirrored into the raw memory DB for fleet management, but is not required for the memory model.

#### Global Raw Memory DB (Idetic + LTM/STM Raw Text)
- Stores the canonical idetic event log plus raw text payloads for derived layers.
- Production target: dedicated DB service (Docker container), suitable for concurrency.
- Local dev default: `.chaos/db/raw.sqlite`.

Schema (SQLite/Postgres compatible, conceptual DDL):

```sql
CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idetic_events (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  persona TEXT NOT NULL,
  loop_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  visibility TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_idetic_agent_persona_ts
  ON idetic_events(agent_id, persona, ts);
CREATE INDEX IF NOT EXISTS idx_idetic_agent_persona_loop
  ON idetic_events(agent_id, persona, loop_id);

CREATE TABLE IF NOT EXISTS ltm_entries (
  id TEXT PRIMARY KEY,
  idetic_id TEXT NOT NULL UNIQUE,
  ts TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  persona TEXT NOT NULL,
  loop_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  visibility TEXT NOT NULL,
  summary TEXT NOT NULL,
  importance REAL NOT NULL DEFAULT 0.0,
  embed_status TEXT NOT NULL DEFAULT 'pending',
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ltm_agent_persona_ts
  ON ltm_entries(agent_id, persona, ts);
CREATE INDEX IF NOT EXISTS idx_ltm_agent_persona_loop
  ON ltm_entries(agent_id, persona, loop_id);

CREATE TABLE IF NOT EXISTS stm_entries (
  id TEXT PRIMARY KEY,
  ts_start TEXT NOT NULL,
  ts_end TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  persona TEXT NOT NULL,
  loop_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(agent_id, persona, loop_id)
);
CREATE INDEX IF NOT EXISTS idx_stm_agent_persona_ts_end
  ON stm_entries(agent_id, persona, ts_end);

CREATE TABLE IF NOT EXISTS stm_ltm_map (
  stm_id TEXT NOT NULL,
  ltm_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  PRIMARY KEY (stm_id, ltm_id)
);
CREATE INDEX IF NOT EXISTS idx_stm_ltm_stm_seq
  ON stm_ltm_map(stm_id, seq);
```

#### Vector Store (LTM Embeddings Only)
- Stores embeddings keyed by `ltm_entries.id` from the raw memory DB.
- Runs as a separate service from the raw memory DB in production.
- Local dev default: `.chaos/db/chroma/`.
- Collections are partitioned by agent and persona:
  - `<agent_id>__actor__ltm`
  - `<agent_id>__subconscious__ltm`

Vector item contract:
- Document id: must equal `ltm_entries.id`.
- Document text: must be `ltm_entries.summary`.
- Metadata: must include `agent_id`, `persona`, `kind`, `visibility`, `ts`, `loop_id`, `importance`.
- Filters: Actor retrieval must filter to `agent_id=<agent_id>` and `persona=actor`.
- Deletions: deleting an LTM entry requires deleting the vector item by id.

## References
- [Agentic Architecture Index](index.md)
- [Memory System](agentic-memory-system.md)
- [Architecture Index](../index.md)
