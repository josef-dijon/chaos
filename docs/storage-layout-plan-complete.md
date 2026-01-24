# Plan: Storage Layout + Identity Naming

## Objective
Reduce project-root clutter and support multiple agent identities by:
- Storing all agent artifacts under `.chaos/`.
- Naming identities via filenames: `<agent_id>.identity.json`.
- Renaming the persistent Chroma directory from `chroma_db/` to `memories/`.

## Target Layout
```text
<project>/
  .chaos/
    identities/
      default.identity.json
      <agent_id>.identity.json
    memories/
```

## Implementation Notes
- CLI commands accept `--agent/-a` to select which identity file to use.
- The default agent id is `default`.
- Persistent memory path defaults to `.chaos/memories` via configuration.

## Verification
- `uv run chaos init` creates `.chaos/identities/default.identity.json`.
- `uv run chaos do "..."` creates `.chaos/memories/` (Chroma persistence).
- No `identity.json` or `chroma_db/` is created in the project root.
