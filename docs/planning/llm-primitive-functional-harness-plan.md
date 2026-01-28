# LLM Primitive Functional Harness Plan

## Status
Draft

## Purpose
Create a simple runnable script that exercises `LLMPrimitive` with a system prompt and Pydantic schema to enable manual functional testing.

## Scope
In scope:
- Add a script under `scripts/` that builds an `LLMPrimitive`, calls `execute`, and prints the result.
- Use `Config` for model/API key resolution.
- Provide a minimal prompt and schema that validates model output.

Out of scope:
- Automated integration tests with real network calls.
- Changes to the core block runtime.

## Contents

### Implementation Steps
1. Add `scripts/llm_primitive_demo.py` with:
   - Pydantic schema for a minimal JSON response.
   - System prompt that instructs JSON-only output.
   - Execution path that prints successful response data or failure details.
2. Update the planning index.

### Acceptance Criteria
- Script runs via `uv run python scripts/llm_primitive_demo.py`.
- With a valid API key, the script prints a parsed response dict.
- Without a key, the script exits with a clear message.

## References
- [Planning Index](index.md)
- [LLM Primitive](../architecture/core/02-llm-primitive.md)
- [Architecture Index](../architecture/index.md)
