## Goal
Define and implement a masked identity schema for the subconscious, driven by tuning policy, with per-field weights and detailed parameter descriptions.

## Scope
- Add weights to identity schema fields to communicate tuning sensitivity.
- Expand field descriptions across identity-related models to guide subconscious tuning.
- Generate a masked, tunable JSON schema filtered by tuning policy and implicit blacklist.
- Ensure subconscious only receives masked schema/identity content.
- Document identity parameters, weights, and tuning policy in a new docs/identity.md.

## Non-Goals
- Changing identity persistence format or file location.
- Allowing subconscious to modify new identity fields beyond policy-driven updates.

## Constraints
- Masked schema must remove any blacklisted path entirely.
- Masking must treat parent-path scopes as covering children.
- Weights must be present for every tunable parameter.
- Subconscious must never see unmasked identity content or schema.

## Design
- Store weights in `json_schema_extra` for each field, using a 1-10 scale.
- Implement `Identity.get_tunable_schema()` to:
  - Build the JSON schema.
  - Inline `$ref` definitions so identical types can be masked differently by path.
  - Walk schema properties and filter by tuning policy and implicit blacklist.
  - Remove empty objects from the schema.
- Provide a helper to return a masked identity view for subconscious usage.

## Implementation Steps
1. Add weights and expand descriptions on identity-related models.
2. Implement schema inlining and policy-based masking in `Identity`.
3. Update subconscious-facing code paths to use masked schema/identity data.
4. Add tests for schema masking and weight presence.
5. Write `docs/identity.md` with parameter descriptions and tuning guidance.
6. Run tests via `uv` and ensure coverage expectations are met.

## Risks & Mitigations
- Risk: masking removes required schema nodes. Mitigation: tests for expected paths.
- Risk: schema inlining is incomplete. Mitigation: recursive `$ref` resolution tests.
