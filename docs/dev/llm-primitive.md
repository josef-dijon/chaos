# LLM Primitive Block

## Status
Stable

## Purpose
Explain how to use the LLM Primitive block as a user-facing building block for schema-validated LLM interactions, including configuration, inputs/outputs, and operational behavior.

## Scope
This document covers usage, configuration, inputs/outputs, metadata, and failure modes for the LLM Primitive block. It does not define architecture or internal implementation details.

## Contents

### Overview
The LLM Primitive block is a stateless, schema-driven LLM wrapper. It takes a prompt, enforces a response schema, and returns a structured `Response` with metadata for observability and usage accounting. It is the primary way to integrate LLM outputs into blocks or composite graphs while keeping validation deterministic.

### When to Use It
- You need structured output (Pydantic schema validation).
- You want stable error reasons (rate limits, auth errors, context length).
- You want usage/cost metadata recorded with each attempt.
- You are composing LLM calls inside larger block graphs.

### Inputs and Outputs
**Input payload**
- A string prompt, or
- A dict with one of: `prompt`, `content`, or `input` (string values).

**Output**
- `Response.success` is `True` when output validates.
- `Response.data` contains the parsed schema object.
- `Response.metadata` includes usage and model details when available.

### Configuration
The block is configured at construction time:

```python
from pydantic import BaseModel

class Summary(BaseModel):
    title: str
    bullet_points: list[str]

llm = LLMPrimitive(
    name="summarizer",
    system_prompt="Return a JSON summary with title and bullet_points.",
    output_data_model=Summary,
    model="gpt-4o-mini",
    temperature=0.2,
    output_retries=2,
)
```

**Provider configuration**
- Default model comes from `Config.model_name` when `model` is not provided.
- Set `OPENAI_API_KEY` to authenticate with the provider.
- Optional proxy routing:
  - `LITELLM_PROXY_URL` enables proxy routing when `litellm_use_proxy` is true.
  - `LITELLM_PROXY_API_KEY` optionally authenticates to the proxy.

### Execution Flow
1. The payload is normalized into a prompt string.
2. A system + user message list is constructed.
3. The model is invoked via the LLM service.
4. Output is validated against the schema.
5. The block returns a `Response` with data or failure details.

### Retry and Recovery Behavior
LLMPrimitive handles retries internally at the provider/schema layers:
- Provider/client retries are handled by the LLM service.
- Schema validation retries are handled internally (controlled by `output_retries`).

Composite block recovery policies should not attempt to retry LLMPrimitive for LLM-facing failures; those errors are bubbled once internal retries are exhausted.

### Errors and Failure Reasons
Typical `Response.reason` values include:
- `schema_error`
- `rate_limit_error`
- `api_key_error`
- `context_length_error`
- `llm_execution_failed`
- `invalid_payload`

Errors always include sanitized `Response.details`, and `Response.error_type` is set for policy selection.

### Metadata and Observability
On success or failure, metadata can include:
- `model`
- `llm.execution_id`
- `llm.attempt`
- `llm_calls`
- `llm.retry_count`
- `input_tokens`
- `output_tokens`

When run inside a composite block, responses also carry correlation metadata such as trace IDs, span IDs, and node names.

### Estimation and Cost Awareness
LLMPrimitive provides a side-effect-free estimate via `estimate_execution`. When stats exist, estimates are derived from historical records; otherwise a conservative prior is used.

### Example Usage
```python
from chaos.domain.messages import Request

request = Request(payload="Summarize this meeting: ...")
response = llm.execute(request)

if response.success:
    print(response.data)
else:
    print(response.reason)
```

### Troubleshooting
- **Schema errors:** Ensure the system prompt matches the schema and output is JSON-compatible.
- **Context length errors:** Reduce prompt size or pick a model with a larger context window.
- **Auth errors:** Check `OPENAI_API_KEY` or proxy credentials.
- **Rate limits:** Back off and retry the overall workflow rather than wrapping LLMPrimitive with extra retries.

## References
- [Developer Index](index.md)
- [LLM Primitive Architecture](../architecture/core/02-llm-primitive.md)
- [Block Responses](../architecture/core/block-responses.md)
