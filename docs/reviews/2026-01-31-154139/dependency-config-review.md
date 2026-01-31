# Dependency Config Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: pyproject.toml
  Issue: All runtime and dev dependencies are specified with only lower bounds (`>=`) and no upper bounds or lockfile pinning strategy.
  Impact: Version drift can introduce breaking API changes or behavior regressions without any code change, making builds non-reproducible and fragile over time.
  Recommendation: Add upper bounds (e.g., `<2`) for core dependencies or adopt a lockfile/pinning workflow with `uv` (e.g., `uv lock` and `uv sync`) to ensure reproducible installs.
  Architecture alignment: Unknown

- Severity: High
  File: src/chaos/config.py
  Issue: `Config.load()` uses `model_validate(payload)` which bypasses `BaseSettings` sources, so environment variables and `.env` are ignored whenever a JSON config exists.
  Impact: Deploy-time overrides (secrets, endpoints, model settings) silently stop working, increasing risk of running with stale or checked-in values.
  Recommendation: Load JSON via `Config(**payload)` or implement a custom settings source order that merges JSON with env, explicitly documenting precedence (env should override file for secrets).
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/config.py
  Issue: `litellm_use_proxy` does not enforce required companion settings (proxy URL and API key), so invalid proxy configurations can pass schema validation.
  Impact: Runtime failures or silent misrouting occur if proxy mode is enabled without a URL or credentials, making production behavior unpredictable.
  Recommendation: Add a model validator to require `litellm_proxy_url` (and optionally `litellm_proxy_api_key`) when `litellm_use_proxy` is true, and document the expected override rules.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/test_config.py
  Issue: Configuration tests do not cover environment-variable overrides or `.env` precedence relative to JSON files.
  Impact: A critical config precedence bug (env ignored when JSON exists) could ship unnoticed, and future changes to settings sources are unguarded.
  Recommendation: Add tests that set `OPENAI_API_KEY`/`CHAOS_*` env vars and verify they override JSON, plus a test for proxy-required fields when `litellm_use_proxy` is true.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/config.py
  Issue: The JSON config schema accepts `openai_api_key` in cleartext without any guardrails or separation guidance.
  Impact: Secrets are likely to end up in local files or checked into repositories, and no runtime mechanism discourages or prevents this.
  Recommendation: Prefer env-only secrets by documenting `openai_api_key` as env-only, optionally add validation that rejects keys in JSON unless an explicit allow flag is set.
  Architecture alignment: Unknown
