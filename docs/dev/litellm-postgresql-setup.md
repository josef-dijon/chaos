# LiteLLM + PostgreSQL Setup

## Status
Stable

## Purpose
Provide user-facing setup requirements for running the LiteLLM proxy and its PostgreSQL backing store used by the LLM Primitive workflow.

## Scope
This guide covers environment prerequisites, minimal LiteLLM proxy configuration, PostgreSQL requirements, and how to point Chaos at the proxy. It does not cover architecture or internal implementation details.

## Contents

### Overview
Chaos can route LLM requests through a LiteLLM proxy for usage tracking and operational controls. The proxy persists usage and cost data to PostgreSQL. This guide explains the minimum setup needed to run both services and connect Chaos.

### Requirements
- Python tooling via `uv` (already required by this project).
- A running LiteLLM proxy server.
- A reachable PostgreSQL instance for proxy persistence.

### LiteLLM Proxy Setup
LiteLLM must be started with a database connection string and a listen address.

Example (environment variables):
```bash
export DATABASE_URL="postgresql://litellm:litellm@localhost:5432/litellm"
export LITELLM_PROXY_PORT=4000
```

Then start the proxy using your preferred LiteLLM deployment method (Docker, pip, or system service). Ensure the proxy is reachable at:
```
http://localhost:4000
```

### PostgreSQL Setup
PostgreSQL must be available before starting the LiteLLM proxy.

Minimum requirements:
- Create a database (example: `litellm`).
- Create a user with permissions to read/write that database.
- Expose a connection string via `DATABASE_URL`.

Example (local):
```bash
createdb litellm
createuser litellm
```

### Configure Chaos to Use the Proxy
Set the following environment variables (or JSON config) when you want Chaos to route LLM calls through LiteLLM:

```bash
export LITELLM_PROXY_URL="http://localhost:4000"
export LITELLM_PROXY_API_KEY="<optional-proxy-key>"
```

If you are also using direct OpenAI credentials, set:
```bash
export OPENAI_API_KEY="<your-openai-key>"
```

### Verification Checklist
- LiteLLM proxy is reachable at `LITELLM_PROXY_URL`.
- PostgreSQL is reachable at `DATABASE_URL` from the proxy environment.
- Chaos requests succeed when `litellm_use_proxy` is enabled.

### Troubleshooting
- **Proxy rejects requests:** Validate `LITELLM_PROXY_API_KEY` and proxy auth settings.
- **No usage data:** Confirm PostgreSQL connectivity and that LiteLLM is configured to persist usage.
- **Connection errors:** Check that `LITELLM_PROXY_URL` matches the proxy host/port.

## References
- [Developer Index](index.md)
- [LLM Primitive Block](llm-primitive.md)
