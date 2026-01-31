# LLM Primitive Review Remediation Checklist (2026-01-31)

## Status
Draft

## Contents

### Architecture-first alignment
- [x] Update `docs/architecture/core/block-request-metadata.md` to align payload typing (Any), request envelope ids, and duration typing.
- [x] Update `docs/architecture/core/02-llm-primitive.md` to align input contract (string payload) and clarify retry layers.
- [x] Update `docs/architecture/core/block-interface.md` to either enforce execution state or mark it informational-only.
- [x] Update `docs/architecture/core/block-responses.md` to align with single canonical success field naming.

### Security & privacy
- [x] Add a shared sanitizer that redacts secrets and caps error detail size.
- [x] Sanitize `src/chaos/llm/llm_error_mapper.py` mappings to avoid raw `str(error)`/`str(cause)` in user-visible details.
- [x] Sanitize unhandled exception conversion in `src/chaos/domain/block.py` (no raw `str(e)` in Response.details).
- [x] Convert API key fields in `src/chaos/config.py` to `SecretStr` and exclude from dumps/repr by default.
- [x] Convert `api_key` field in `src/chaos/llm/llm_request.py` to `SecretStr` (or dedicated credential wrapper) and exclude from dumps/repr.
- [x] Enforce fail-closed behavior when `litellm_use_proxy=True` but proxy URL is missing.
- [x] Add stats retention/rotation and restrict file permissions for on-disk stats.
- [x] Update `scripts/llm_primitive_demo.py` to avoid printing raw failure details by default; add `--debug` for verbose output.

### Config correctness & dependency hygiene
- [ ] Fix `src/chaos/config.py:Config.load()` so env/.env overrides are applied even when JSON config exists.
- [ ] Add validator in `src/chaos/config.py` requiring `litellm_proxy_url` (and key if required) when `litellm_use_proxy` is true.
- [ ] Add tests in `tests/test_config.py` for env precedence over JSON.
- [ ] Add tests in `tests/test_config.py` for proxy-required-field validation.
- [ ] Decide on reproducible dependency strategy and implement (upper bounds and/or `uv lock` workflow).

### Observability & metadata propagation
- [ ] Ensure every Request has `metadata["id"]` generated on creation.
- [ ] Ensure child requests regenerate `metadata["id"]` each time.
- [ ] Fix composite terminal response metadata attachment in `src/chaos/domain/block.py` to overwrite correlation fields (not setdefault).
- [ ] Ensure `src/chaos/domain/block.py:_record_attempt` logs exceptions instead of swallowing silently.
- [ ] Add structured logging for unhandled exceptions in `Block.execute` with trace/run/span/id/block/node.
- [ ] Namespace internal retry counters (e.g., `llm.attempt`, `llm.retry_count`) and update consumers.
- [ ] Propagate trace/run/span identifiers to provider calls if supported, or emit structured logs around provider calls.

### Recovery semantics & error handling
- [ ] Ensure `unknown_node` failures in `src/chaos/domain/block.py` set `error_type` deterministically.
- [ ] Ensure all failure Responses set `error_type` consistently across graph execution paths.
- [ ] Implement `RetryPolicy.delay_seconds` behavior in `_execute_child_with_recovery`.
- [ ] Define and implement `RetryPolicy.max_attempts` as total attempts (fix off-by-one behavior).
- [ ] Preserve original `error_type` and include prior `reason/details` in `unsafe_to_retry` responses.
- [ ] Catch exceptions thrown inside `condition_func(response)` and return a failure with condition context.
- [ ] Tighten `src/chaos/llm/llm_service.py:LLMService.execute` to only map known provider errors; treat unexpected exceptions as internal errors.
- [ ] Decide and act on `ResponseStatus.BUDGET_ERROR`: implement end-to-end mapping or remove the enum value and dead paths.
- [ ] Replace broad substring matching for context-length errors with provider-code detection when available.
- [ ] Make default stats store resilient to corrupt JSON stats file (no crash on import/startup).

### Performance & scalability
- [ ] Cache graph validation on build/setup and skip per-execution validation.
- [ ] Reduce deep-copy usage for Requests and terminal Responses (prefer shallow copies + metadata-only updates).
- [ ] Cache/reuse LLM clients/models in `src/chaos/llm/llm_service.py` to avoid per-request construction.
- [ ] Cache/reuse agents in `_run_agent` where safe.
- [ ] Replace `src/chaos/stats/json_block_stats_store.py` rewrite-per-attempt with append-only journaling or batched writes + rotation.
- [ ] Add an index (by block identity) to make `estimate` faster than scanning all records.
- [ ] Add bounded retention to prevent unbounded in-memory record growth.
- [ ] Optionally replace `mean_std` with a streaming algorithm if needed for large samples.

### Dependency inversion & testability
- [ ] Make `src/chaos/stats/store_registry.py` default store lazy (no import-time Config/file I/O).
- [ ] Add an injectable ID factory for request/response ids to make metadata tests deterministic.
- [ ] Add an injectable stats store dependency to `Block` to avoid patching globals in tests.
- [ ] Add injectable registry/policy handler seams for recovery logic (or move orchestration out of domain layer).
- [ ] Make `LLMPrimitive` construction side-effect free (avoid default `Config.load()` / disk reads in `__init__`).

### DRY, naming, and API cleanup
- [ ] Refactor `Block._execute_child_with_recovery` into smaller helpers.
- [ ] Extract a single unsafe-to-retry helper used by both RetryPolicy and RepairPolicy branches.
- [ ] Remove `src/chaos/llm/model_selector.py` if it is still a no-op; update call sites and delete/update `tests/llm/test_model_selector.py`.
- [ ] Remove redundant `LLMPrimitive.get_policy_stack` override if it matches the base behavior.
- [ ] Rename `manager_id` to `execution_id` (or `correlation_id`) consistently across `LLMPrimitive`, `LLMRequest`, and metadata.
- [ ] Remove duplicated sources of truth for attempt/execution ids (single authoritative location).
- [ ] Standardize on a single Response success field name (`success`) and remove aliasing (`ok`).
- [ ] Fix `_run_agent` system prompt typing and stop passing `()` for missing prompts.
- [ ] Remove or implement request-aware estimation; if removing, update `src/chaos/stats/estimate_builder.py` signatures/docs and tests.
- [ ] Replace free-form `side_effect_class` with an enum or Literal, validate at construction.
- [ ] Replace free-form estimate source/confidence strings with enums or Literals.
- [ ] Centralize schema error mapping logic in `src/chaos/llm/llm_error_mapper.py` to avoid duplicated branches.
- [ ] Define and document composite metadata keys (`source`, `composite`, `last_node`) via constants/schema.

### Tests, docs, and verification
- [ ] Add tests for metadata id generation and propagation (root + child + retries/repairs).
- [ ] Add tests for composite correlation metadata overwrite behavior.
- [ ] Add tests for retry semantics: delay usage, max_attempts count, unsafe_to_retry preservation.
- [ ] Add tests for condition function exception handling.
- [ ] Add tests for error sanitization (no sensitive strings in responses).
- [ ] Add tests for proxy fail-closed behavior.
- [ ] Add tests for LLMService mapping boundaries and 401/403 auth mapping.
- [ ] Update test helpers to match real API shapes (e.g., ModelSettings access in FakeAgent).
- [ ] Add docstrings to test functions/helpers to meet project standard.
- [ ] Run `uv run pytest` and confirm coverage >= 95%.
- [ ] Ensure architecture docs remain the source of truth and match implementation after changes.

## References
- [LLM Primitive Review Remediation Plan](llm-primitive-review-remediation-plan.md)
- `docs/reviews/2026-01-31-154139/`
