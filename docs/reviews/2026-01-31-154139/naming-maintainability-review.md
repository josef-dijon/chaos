# Naming Maintainability Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: The identifier name `manager_id` and `_build_manager_id` are domain-opaque; “manager” does not describe what is being managed (request, execution, trace, or correlation).
  Impact: Readers cannot infer whether this is a request-id, execution-id, or audit correlation id, making cross-service tracing harder to maintain and easy to misuse.
  Recommendation: Rename to something explicit like `execution_id` or `correlation_id` and align field names in `LLMRequest`/metadata to the same term.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_execute_child_with_recovery` mixes retry, repair, and generic policy handling with deep nesting and repeated request/response bookkeeping.
  Impact: Complex control flow makes recovery behavior hard to reason about and risky to modify, increasing maintenance cost and bug likelihood.
  Recommendation: Split into smaller helpers (e.g., `_apply_retry_policy`, `_apply_repair_policy`, `_apply_generic_policy`) and keep the high-level loop declarative.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: Response uses `ok` as the field name but exposes `success` as an alias, while most call sites pass `success=` and use `success()` method.
  Impact: Dual naming creates cognitive overhead and easy-to-miss inconsistencies when refactoring or searching usages.
  Recommendation: Pick a single canonical field name (`success` preferred for clarity) and remove the alias/secondary name.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but `LLMPrimitive` accepts raw `str` payloads and treats dict keys as optional fallbacks.
  Impact: The public request contract is unclear and encourages inconsistent call patterns, making API usage harder to discover and validate.
  Recommendation: Widen `payload` type to `Any` or introduce a dedicated `prompt` field/type for LLM primitives and document the expected shapes.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block_estimate.py
  Issue: `estimate_source` and `confidence` are free-form strings with no enum/typed guardrails.
  Impact: Inconsistent or misspelled values are easy to introduce, reducing downstream readability and making analytics brittle.
  Recommendation: Replace with enums (or `Literal[...]`) and document the allowed values in one place.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `side_effect_class` is a free-form string with normalization logic and magic values scattered across the class.
  Impact: New contributors can introduce incompatible values, and the normalization behavior is easy to miss.
  Recommendation: Use an enum (or `Literal`) for side effect classes and validate at construction time to make intent explicit.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_request.py
  Issue: `manager_id` is stored both as a top-level field and duplicated in `metadata`, but only metadata appears to be consumed.
  Impact: Redundant fields invite drift and make it unclear which value is authoritative when debugging requests.
  Recommendation: Keep a single source of truth (either top-level `manager_id` or `metadata['manager_id']`) and remove the duplicate.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_error_mapper.py
  Issue: `map_llm_error` contains duplicated branches that map multiple schema-related cases to the exact same `LLMErrorMapping`.
  Impact: Redundant logic makes the function longer and harder to audit, increasing the chance of inconsistent edits.
  Recommendation: Consolidate schema-error checks into a single guard (e.g., helper predicate) and return once.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/messages.py
  Issue: `Response.__init__` mutates `metadata` by injecting an `id` field, but this implicit behavior is undocumented in the model fields.
  Impact: Hidden side effects make response creation harder to reason about and can surprise maintainers who rely on metadata being caller-owned.
  Recommendation: Document the auto-generated `metadata.id` (field description or class docstring) or expose it as an explicit field.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: Composite terminal responses inject `source`, `composite`, and `last_node` into `Response.metadata` without any explicit contract or typed structure.
  Impact: Downstream code has to rely on undocumented ad-hoc keys, making API ergonomics and refactors brittle.
  Recommendation: Define a structured metadata schema (or constants) for these keys and document them in the public response contract.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: `_DEFAULT_STORE` is constructed at import time via `Config.load()`, which can read disk and bind config before callers have a chance to configure paths.
  Impact: Hidden side effects at import make behavior order-dependent and harder to test or override cleanly.
  Recommendation: Lazy-load the default store on first access, or move initialization into an explicit setup function.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Metadata uses both `attempt` and `block_attempt`, with `attempt` coming from the request and `block_attempt` reintroduced in `_build_llm_request`.
  Impact: Multiple names for the same concept make logs and downstream analytics harder to interpret and maintain.
  Recommendation: Standardize on a single field name for block attempt metadata and remove the redundant alias.
  Architecture alignment: Unknown
