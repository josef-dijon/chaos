## Goal
Define and implement a tuning policy that uses path-based allow/deny lists to control what the subconscious can modify on an identity, with explicit precedence and an implicit blacklist for protected fields.

## Scope
- Replace boolean tuning policy flags with path-based `whitelist` and `blacklist`.
- Enforce path-scoping rules with parent-path coverage.
- Ensure blacklist always overrides whitelist.
- Add implicit blacklisted fields in Identity to prevent modifications of core and safety-critical fields.
- Update agent and identity mutation flows to use the new policy.
- Add tests for scoping, precedence, and implicit blacklist behavior.

## Non-Goals
- Changing the identity schema format beyond the tuning policy fields.
- Adding new subconscious capabilities beyond updating identity fields already supported.

## Constraints
- The subconscious must never be able to edit `tuning_policy`.
- Implicit blacklist includes: `schema_version`, `tuning_policy`, `memory.subconscious`, `memory.actor`, `loop_definition`.
- Blacklist has higher priority than whitelist for any scoped or parent path.
- Path strings use dot-separated identity fields (e.g., `profile.name`).

## Design
- `TuningPolicy` will contain:
  - `whitelist: List[str]`
  - `blacklist: List[str]`
- Add `TuningPolicy.is_allowed(target_path: str, implicit_blacklist: List[str]) -> bool`.
  - If `target_path` is covered by any implicit blacklist path -> deny.
  - If `target_path` is covered by any explicit blacklist path -> deny.
  - If `target_path` is covered by any whitelist path -> allow.
  - Default deny.
- Add helper to detect coverage: a path `a.b` covers `a.b` and `a.b.c`.
- Add `IDENTITY_IMPLICIT_TUNING_BLACKLIST` in `Identity` and use it for policy checks.
- Update `Agent.learn` to check `is_allowed("instructions.operational_notes", ...)`.
- Default policy should allow operational notes updates (e.g., whitelist includes `instructions.operational_notes`).

## Implementation Steps
1. Update architecture spec to document tuning policy allow/deny lists and implicit blacklist.
2. Refactor `TuningPolicy` to new schema and implement access checks.
3. Update `Identity` to define implicit blacklist and use policy in mutation methods.
4. Update `Agent.learn` to use policy check instead of boolean flag.
5. Update or add tests for policy scoping and identity mutation rules.
6. Run tests via `uv` and ensure coverage expectations are met.

## Risks & Mitigations
- Risk: breaking existing identity JSON. Mitigation: provide sane defaults in model fields.
- Risk: unintended permission gaps. Mitigation: add targeted tests for precedence and scope.
