# LLM Primitive Review Remediation Plan (2026-01-31)

## Status
Draft

## Purpose
Address the issues raised in the latest review set under `docs/reviews/2026-01-31-154139/` by updating code, tests, and architecture documentation.

This repo is pre-release, so API breakage is acceptable. The goal is to converge on a single, coherent contract for:
- request/response payload types
- correlation metadata propagation
- recovery semantics
- secure error handling
- config precedence (env vs JSON)
- stats storage scalability

## Inputs (Reviews)
- `docs/reviews/2026-01-31-154139/master-review.md`
- `docs/reviews/2026-01-31-154139/architecture-solid-review.md`
- `docs/reviews/2026-01-31-154139/error-handling-review.md`
- `docs/reviews/2026-01-31-154139/logging-observability-review.md`
- `docs/reviews/2026-01-31-154139/security-privacy-review.md`
- `docs/reviews/2026-01-31-154139/dependency-config-review.md`
- `docs/reviews/2026-01-31-154139/performance-scalability-review.md`
- `docs/reviews/2026-01-31-154139/dry-deadcode-review.md`
- `docs/reviews/2026-01-31-154139/python-best-practices-review.md`
- `docs/reviews/2026-01-31-154139/naming-maintainability-review.md`
- `docs/reviews/2026-01-31-154139/documentation-review.md`

## Scope
### Code
- Domain/runtime:
  - `src/chaos/domain/block.py`
  - `src/chaos/domain/messages.py`
  - `src/chaos/domain/llm_primitive.py`
  - `src/chaos/domain/policy.py`
  - `src/chaos/domain/exceptions.py`
- LLM layer:
  - `src/chaos/llm/llm_service.py`
  - `src/chaos/llm/llm_request.py`
  - `src/chaos/llm/llm_response.py`
  - `src/chaos/llm/llm_error_mapper.py`
  - `src/chaos/llm/response_status.py`
  - `src/chaos/llm/model_selector.py` (likely removal)
- Stats/config:
  - `src/chaos/stats/store_registry.py`
  - `src/chaos/stats/json_block_stats_store.py`
  - `src/chaos/stats/estimate_builder.py`
  - `src/chaos/stats/statistics.py`
  - `src/chaos/config.py`
- Scripts:
  - `scripts/llm_primitive_demo.py`

### Tests
- `tests/domain/test_llm_primitive.py`
- `tests/llm/test_llm_service.py`
- `tests/llm/test_model_selector.py` (likely removal/update)
- `tests/stats/test_block_estimation.py`
- `tests/test_config.py`

### Architecture / Docs
- `docs/architecture/core/02-llm-primitive.md`
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/block-request-metadata.md`
- `docs/architecture/core/recovery-policy-system.md`
- `docs/architecture/core/block-estimation.md`

## Target Contract Decisions (API breakage allowed)
1. Request payload typing:
   - `Request.payload` becomes `Any` (architecture says payload is not dict-only).
   - Individual blocks (e.g., LLMPrimitive) enforce their own payload requirements.
2. LLMPrimitive input contract:
   - Enforce string payloads for LLMPrimitive (match architecture) and remove dict-envelope coercion.
3. Correlation metadata:
   - Every Request envelope has a unique `metadata["id"]`.
   - Child requests always regenerate `metadata["id"]`.
   - Composite terminal responses overwrite correlation identifiers with the composite request identifiers.
4. Response shape:
   - Use a single canonical success field name (`success`) and remove dual naming (`ok` alias).
5. Naming:
   - Rename `manager_id` to `execution_id` (or `correlation_id`) end-to-end and eliminate duplicates.
6. Retry semantics:
   - Define `RetryPolicy.max_attempts` as total attempts (including the first attempt).
   - Apply `RetryPolicy.delay_seconds` (and optionally jitter) between attempts.
7. Errors and privacy:
   - Never return raw exception strings by default; sanitize and cap all user-facing `details`.
   - Secrets are stored as `SecretStr` and excluded from dumps/repr by default.
8. Default store initialization:
   - No import-time filesystem/config side effects; default stats store is lazy and resilient to corrupt files.

## Plan
### 1) Architecture-first updates (source of truth)
1. Update `docs/architecture/core/block-request-metadata.md`:
   - Confirm payload is `Any`.
   - Specify request envelope `metadata.id` generation and regeneration on child envelopes.
   - Clarify context pruning responsibility (caller vs base class), and align `duration_ms` type.
2. Update `docs/architecture/core/02-llm-primitive.md`:
   - Make LLMPrimitive payload contract `str` explicit.
   - Document config/constructor surface that materially changes behavior.
   - Clarify retry layers (provider/API retries vs schema retries vs block recovery).
3. Update `docs/architecture/core/block-interface.md`:
   - Decide whether state is informational-only or enforced; align with implementation.

### 2) Security & privacy remediation (highest priority)
1. Add a shared error sanitization utility:
   - Redact likely secrets (API keys, auth headers), cap sizes, and avoid embedding prompts/outputs.
2. Update `src/chaos/llm/llm_error_mapper.py`:
   - Remove raw `str(error)` / `str(__cause__)` from `details`.
   - Prefer stable error codes + safe structured fields.
3. Update `src/chaos/domain/block.py`:
   - Replace raw exception strings in unhandled exception failures with sanitized, stable details.
4. Convert secrets to `SecretStr`:
   - `src/chaos/config.py` API key fields.
   - `src/chaos/llm/llm_request.py` request credential fields.
5. Fail closed for proxy routing:
   - If `litellm_use_proxy` is true, require proxy URL (and key if required) or raise a configuration error.
6. Stats privacy hygiene:
   - Add retention/rotation and restrictive permissions for on-disk stats.
7. Demo script output:
   - Make `scripts/llm_primitive_demo.py` print stable error codes by default; gate verbose details behind a debug flag.

### 3) Config correctness & precedence
1. Fix `Config.load()` behavior so JSON does not bypass env/.env overrides.
2. Add validators to enforce required proxy companion settings when proxy mode is enabled.
3. Add tests in `tests/test_config.py`:
   - env overrides JSON
   - proxy required fields
4. Adopt a reproducible dependency strategy:
   - add upper bounds and/or establish `uv lock` workflow.

### 4) Observability & metadata correctness
1. Request envelope IDs:
   - Generate `metadata["id"]` in `Request` (or in base metadata composition) and regenerate for child envelopes.
2. Composite correlation overwrites:
   - When composites synthesize terminal responses, overwrite correlation keys in response metadata (do not preserve child ids via setdefault).
3. Logging:
   - Log unhandled exceptions in `Block.execute` with trace/run/span/id/block/node.
   - Log stats recording failures in `_record_attempt` with correlation identifiers.
4. Namespaced internal counters:
   - Rename internal retry/attempt metadata keys to namespaced forms per the metadata guidelines.
5. Provider correlation:
   - Pass trace/run/span identifiers to provider metadata/tags if supported; otherwise emit structured logs around provider calls.

### 5) Recovery semantics and error handling
1. Ensure all failure `Response`s populate `error_type` deterministically (including unknown-node/invalid-graph paths).
2. Implement retry delay handling (`delay_seconds`) and fix `max_attempts` off-by-one.
3. Preserve root-cause details through `unsafe_to_retry` gating.
4. Catch exceptions thrown by condition functions and emit condition-context failures.
5. Tighten exception mapping boundaries in `LLMService.execute`:
   - Map known provider errors; surface unexpected exceptions as internal errors.
6. Remove or implement dead enums/paths:
   - Decide and act on `ResponseStatus.BUDGET_ERROR`.
7. Improve context-length classification:
   - Prefer provider codes/fields; fall back to message substrings only when necessary.

### 6) Performance and scalability
1. Cache graph validation at build/setup time; do not revalidate on each execute.
2. Reduce deep-copy churn by doing shallow copies and targeted metadata mutation.
3. Cache or reuse provider clients/models/agents where safe.
4. Replace JSON stats rewrite-per-attempt:
   - Implement append-only (JSONL/journal) + periodic compaction, or batching + rotation as a minimal fix.
   - Add bounded retention and an index for faster `estimate`.
5. Evaluate `mean_std` streaming algorithm if large sample sizes become common.

### 7) Dependency inversion and testability refactor
1. Remove import-time side effects:
   - make default store lazy and resilient to corrupted files.
2. Add injection seams:
   - ID factory for deterministic metadata IDs.
   - stats store injection to avoid patching globals.
   - registries/policy handlers injection (or move orchestration out of domain layer if architecture dictates).
3. Make constructors side-effect free:
   - avoid default `Config.load()` inside domain constructors.

### 8) Maintainability cleanup (DRY, naming, typing)
1. Refactor `Block._execute_child_with_recovery` into small helpers.
2. Extract a single unsafe-to-retry helper shared by RetryPolicy/RepairPolicy.
3. Remove `ModelSelector` if it remains a no-op; update call sites/tests.
4. Fix `_run_agent` system prompt typing and behavior.
5. Remove unused API surface (e.g., unused estimation `request` param) or implement request-aware estimation.
6. Standardize typed enumerations for:
   - `side_effect_class`
   - estimate source/confidence
7. Document metadata keys used by composites and standardize them via constants.

### 9) Tests and verification
1. Add unit tests covering:
   - request id generation and propagation
   - composite correlation overwrite
   - retry limits + delay behavior
   - unsafe-to-retry preservation
   - condition function exception handling
   - config precedence and proxy fail-closed behavior
   - error sanitization (no raw prompts/keys in responses)
2. Remove/update tests that only validate no-op behaviors (e.g., ModelSelector passthrough).
3. Add docstrings to test helpers and test cases to meet the repo standard.
4. Run `uv run pytest` and confirm coverage >= 95%.

## Outputs
- Code changes implementing secure error handling, correct metadata propagation, deterministic recovery semantics, scalable stats storage, and improved DI.
- Updated tests with expanded coverage for recovery + metadata contracts.
- Updated architecture docs aligned with actual contracts.

## References
- `docs/planning/index.md`
- `docs/reviews/2026-01-31-154139/`
- `docs/architecture/index.md`
