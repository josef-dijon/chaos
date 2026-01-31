# LLM Primitive Functional Test Plan

## Status
Stable

## Purpose
Provide a user-facing, end-to-end functional test plan for the LLM Primitive block using a running LiteLLM proxy and the existing demo script.

## Scope
This plan covers functional verification of success paths, error handling, metadata, and proxy routing using the `scripts/llm_primitive_demo.py` script. It does not include unit tests, architecture details, or implementation-level validation.

## Contents

### Prerequisites
- Docker and Docker Compose.
- `uv` installed.
- A LiteLLM proxy configured with provider keys (see `docs/dev/litellm-postgresql-setup.md`).
- A working `.env` with the required settings (see `.env.sample`).

### Environment Setup
1. Create a local environment file:
   ```bash
   cp .env.sample .env
   ```
2. Update `.env` with your provider credentials and any custom ports.
3. Start LiteLLM + Postgres:
   ```bash
   docker compose up -d
   ```

### Chaos Configuration
Enable proxy routing in your Chaos configuration. Create or update `.chaos/config.json`:
```json
{
  "litellm_use_proxy": true,
  "litellm_proxy_url": "http://localhost:4000",
  "model_name": "gpt-4o-mini"
}
```

If you use a proxy key, set `LITELLM_PROXY_API_KEY` in `.env`.

### Test Harness
All tests use the demo script:
```bash
uv run python scripts/llm_primitive_demo.py --prompt "Say hello in JSON."
```

Use `--debug` to include failure details:
```bash
uv run python scripts/llm_primitive_demo.py --prompt "Say hello in JSON." --debug
```

### Functional Test Matrix

#### 1) Happy Path (Schema-Valid JSON)
- **Setup:** Proxy running, valid provider keys.
- **Command:**
  ```bash
  uv run python scripts/llm_primitive_demo.py --prompt "Return {\"response\": \"ok\"}."
  ```
- **Expected:** `Success`, `Response.success` is `True`, output matches schema.

#### 2) Schema Error (Invalid JSON)
- **Command:**
  ```bash
  uv run python scripts/llm_primitive_demo.py --prompt "Reply with plain text, no JSON." --debug
  ```
- **Expected:** `Failure`, `reason` is `schema_error`.

#### 3) API Key Error
- **Setup:** Unset or set an invalid provider key in the LiteLLM environment.
- **Command:**
  ```bash
  uv run python scripts/llm_primitive_demo.py --prompt "Say hello in JSON." --debug
  ```
- **Expected:** `Failure`, `reason` is `api_key_error`.

#### 4) Rate Limit Error
- **Setup:** Trigger rate limits via your provider (e.g., repeated rapid calls) or use a proxy limit.
- **Command:**
  ```bash
  for i in $(seq 1 10); do uv run python scripts/llm_primitive_demo.py --prompt "Say hello in JSON."; done
  ```
- **Expected:** At least one `Failure`, `reason` is `rate_limit_error`.

#### 5) Context Length Error
- **Setup:** Use a large prompt.
- **Command:**
  ```bash
  uv run python scripts/llm_primitive_demo.py --prompt "$(python - <<'PY'
print('A' * 200000)
PY
)" --debug
  ```
- **Expected:** `Failure`, `reason` is `context_length_error`.

#### 6) Proxy Connectivity Error
- **Setup:** Stop the LiteLLM container or point `litellm_proxy_url` to a bad host.
- **Command:**
  ```bash
  uv run python scripts/llm_primitive_demo.py --prompt "Say hello in JSON." --debug
  ```
- **Expected:** `Failure`, `reason` is `llm_execution_failed` or `internal_error`.

#### 7) Invalid Payload Handling
- **Setup:** Edit `scripts/llm_primitive_demo.py` temporarily to pass a non-string payload.
- **Expected:** `Failure`, `reason` is `invalid_payload`.

### Observability Checks
- Confirm `Response.metadata` includes `model`, `llm.execution_id`, `llm.attempt`, and usage fields when available.
- When proxy is enabled, confirm LiteLLM records usage in PostgreSQL.

### Cleanup
- Stop services when finished:
  ```bash
  docker compose down
  ```

## References
- [Developer Index](index.md)
- [LLM Primitive Block](llm-primitive.md)
- [LiteLLM + PostgreSQL Setup](litellm-postgresql-setup.md)
