# Additional Risks Review

Timestamp: 2026-01-31-145336

- Severity: Medium
- File: src/chaos/domain/llm_primitive.py
- Issue: Request metadata is copied into `LLMRequest` without validation/allowlisting, and caller-supplied keys can override values like `block_name`.
- Impact: Untrusted metadata can poison logs/stats, spoof identity fields, or leak arbitrary data to downstream LLM providers if metadata is propagated.
- Recommendation: Enforce a strict allowlist of metadata keys and ignore user-supplied identity fields; populate `block_name`, `manager_id`, and attempts from trusted sources only.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/config.py
- Issue: `litellm_use_proxy` can be true while `litellm_proxy_url` is unset, but no validation enforces a usable proxy configuration.
- Impact: Traffic can silently bypass the proxy (or fail later), causing policy or compliance drift and hard-to-debug routing behavior.
- Recommendation: Validate configuration invariants (if proxy enabled, require proxy URL and/or key) and raise a clear error on startup.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/llm_primitive.py
- Issue: `manager_id` truncates UUIDs to 8 hex characters.
- Impact: Higher collision probability in high-throughput systems, reducing traceability and audit reliability.
- Recommendation: Use full UUIDs or include additional entropy (timestamp or full uuid4 hex).
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/domain/block.py
- Issue: Uncaught exceptions are surfaced to callers with raw `str(e)` in `details`.
- Impact: Internal errors can leak secrets (API keys, prompt content, file paths) to external consumers and logs.
- Recommendation: Replace raw exception strings with sanitized error codes; log full details securely behind a debug flag.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/llm/llm_service.py
- Issue: LLM execution does not set or expose max output/token limits or timeouts in `ModelSettings`.
- Impact: A single request can generate unbounded output, increasing latency and cost; timeouts are provider defaults and may be too high.
- Recommendation: Add configurable `max_tokens` and timeout settings to `LLMRequest`/`Config` and pass them to the model settings.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/stats/in_memory_block_stats_store.py
- Issue: In-memory stats store grows without bounds and has no retention or eviction.
- Impact: Long-running processes will steadily increase memory usage and may degrade or crash under sustained load.
- Recommendation: Add configurable retention (max records/TTL) or disable recording for in-memory store in production.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/stats/json_block_stats_store.py
- Issue: JSON stats store rewrites the entire file on every attempt and uses no file locking or size limits.
- Impact: Concurrent writers can corrupt data, and large histories will cause slow writes and high memory usage.
- Recommendation: Add file locking, append-only or chunked storage, and configurable retention/size limits; consider a proper database backend.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/llm/llm_error_mapper.py
- Issue: Error mapping always includes raw exception and cause strings in `details`.
- Impact: Provider errors can embed secrets (API keys, prompts, URLs), which then flow into responses/logs and risk data leakage.
- Recommendation: Redact sensitive fields, truncate messages, and prefer structured error codes over raw exception strings.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/domain/policy.py
- Issue: `RetryPolicy.delay_seconds` is defined but never honored in execution paths.
- Impact: Operators cannot throttle retries, increasing the risk of rate-limit amplification and noisy retry storms.
- Recommendation: Implement delay/backoff handling in recovery execution or remove the field to avoid misleading configuration.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/block.py
- Issue: `_record_attempt` swallows all exceptions when persisting stats.
- Impact: Stats storage failures become silent, making it hard to detect monitoring gaps or capacity problems.
- Recommendation: Log or surface store write failures (at least at debug/error), and consider a configurable failure policy.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/domain/block.py
- Issue: Recovery loop can execute multiple Retry/Repair policies in sequence without a global attempt budget or backoff.
- Impact: A single failure can trigger a large number of re-executions, increasing cost and latency and amplifying load on downstream services.
- Recommendation: Add a global recovery budget (max total attempts) and backoff/jitter; enforce policy ordering and stop conditions explicitly.
- Architecture alignment: Unknown
