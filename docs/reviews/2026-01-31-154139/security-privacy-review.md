# Security Privacy Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: src/chaos/config.py
  Issue: API keys are stored as plain strings in Config and are not marked secret/excluded from serialization or repr.
  Impact: Secrets can leak into logs, debug output, or accidental JSON dumps of the settings object.
  Recommendation: Use `pydantic.SecretStr` (or equivalent) for API key fields and set `repr=False`/`exclude=True` where appropriate; avoid exposing keys via model_dump unless explicitly requested.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/llm_request.py
  Issue: `api_key` is a plain string field on `LLMRequest`, making it easy to leak via serialization, logging, or exception traces.
  Impact: Accidental leakage of provider credentials into logs or persisted artifacts can compromise the LLM account.
  Recommendation: Replace `api_key: Optional[str]` with `SecretStr` (or a dedicated credential wrapper) and exclude it from `model_dump`/repr by default.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Error mapping captures raw `str(error)` and `str(cause)` into `details` without redaction.
  Impact: Provider exceptions and validation errors often include request/response payloads, which can leak prompts, model outputs, or other sensitive data into user-visible responses or logs.
  Recommendation: Redact/whitelist error fields before storing them, and avoid including raw exception strings in responses by default.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Unhandled exceptions are converted into `Response.details` with raw `str(e)`.
  Impact: Internal exceptions can carry secrets, prompt content, or PII and will be exposed to callers or logs without redaction.
  Recommendation: Replace raw exception strings with stable error codes and sanitized metadata; keep full exceptions only in restricted internal logs.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/stats/json_block_stats_store.py
  Issue: Stats are persisted to a JSON file without retention limits, access controls, or redaction of identifiers.
  Impact: Trace/run identifiers and model metadata can accumulate indefinitely on disk, increasing privacy exposure and forensic risk if the file is read by unauthorized users.
  Recommendation: Add retention/rotation, minimize stored fields, and consider writing with restrictive file permissions (e.g., 0o600) or a secured store.
  Architecture alignment: Unknown

- Severity: Low
  File: scripts/llm_primitive_demo.py
  Issue: Demo script prints raw failure details directly to stdout.
  Impact: Failure details may contain provider error messages or validation payloads that include sensitive prompt/output content, leading to inadvertent disclosure in terminals or logs.
  Recommendation: Redact sensitive fields or print only stable error codes; optionally gate verbose details behind a `--debug` flag.
  Architecture alignment: Not Available

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: When `litellm_use_proxy` is true but no proxy URL is configured, `_resolve_api_settings` silently falls back to direct OpenAI base URL.
  Impact: Intended data-governance/egress controls can be bypassed, sending prompts to the public endpoint without explicit approval.
  Recommendation: Fail closed when proxy usage is enabled but `litellm_proxy_url` is missing; require explicit override to allow direct routing.
  Architecture alignment: Unknown
