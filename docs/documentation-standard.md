# Documentation Standard

This document defines the project-wide documentation standard for an indexed, navigable documentation set.

The documentation hierarchy is rooted at `docs/README.md`, which provides an index and links to the three primary sections:
- `docs/architecture/index.md` (source of truth for architecture)
- `docs/dev/index.md` (developer docs)
- `docs/planning/index.md` (planning and execution artifacts)

All other docs are organized beneath these sections and referenced from their respective section index. This standard applies to architecture docs, developer docs, planning docs, and checklists.

## 1. Structure Rules
- The root index (`docs/README.md`) must link to every top-level section.
- Each section index must be named `index.md` and live at the section root.
- Do not create section indices named `README.md` or `guide.md`.
- Each section index must link to every document in its section.
- Every document must appear in exactly one section index.
- All links must be relative and stable within the repository.
- Legacy content is retained under `docs/migrate_from/` and linked as legacy references only.

## 2. Document Template
All architecture and developer docs should follow this template unless a doc is explicitly an index.

### Title
Use a clear, descriptive title in H1.

### Status
Include one of: Draft, Stable, Deprecated.

### Purpose
Explain what the document covers and why it exists.

### Scope
Define the boundaries of the document (what is in/out of scope).

### Contents
Provide the main content, structured with H2/H3 sections. Use short sections and keep each section tightly focused.

### References
Link to related docs in the same section, and to any relevant legacy references in `docs/migrate_from/` if needed.
Always link back to the section index.

## 3. Index Template
Section index files are indices and should follow this format:

### Overview
Brief description of the section and how to use it.

### Index
Bullet list of documents in that section, each with a one-line description.
Order sections as: Overview, Index, Related.

### Roadmap
List roadmap documents for the section (if any) and include a table with high-level items.
Use this table format:

| Item | Status | Notes |
| --- | --- | --- |
| <short item> | <planned/in-progress/complete> | <short note> |

### Related
Links to other section indexes or legacy references if needed.

#### Planning Index Requirements
The planning index (`docs/planning/index.md`) must include:
- An In Progress section.
- A Complete section.
- Checklists may live in In Progress but must be deleted when the plan moves to Complete.

## 4. Conventions
- Use kebab-case for all documentation file names.
- The only allowed `README.md` is `docs/README.md` at the root.
- Avoid deeply nested directories unless required by content volume.
- Keep documents focused and short; create multiple docs instead of one large one.
- Do not copy large legacy text verbatim. Summarize and link to legacy sources if needed.
- Architecture docs define intent and structure; implementation steps belong in developer docs.
