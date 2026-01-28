# LLM Primitive LiteLLM Integration Checklist

## Status
Draft

## Contents
- [x] Add LiteLLM dependency in `pyproject.toml`.
- [x] Update `LLMPrimitive` to call LiteLLM and parse responses.
- [x] Map provider errors to architecture failure categories.
- [x] Update tests to mock LiteLLM and validate error mapping.
- [x] Update `docs/architecture/core/02-llm-primitive.md` with LiteLLM note.
- [x] Run `uv run pytest` with coverage >= 95%.

## References
- [LLM Primitive LiteLLM Integration Plan](llm-primitive-litellm-plan.md)
