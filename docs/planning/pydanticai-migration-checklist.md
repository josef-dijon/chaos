# PydanticAI Migration Checklist

## Status
Draft

## Contents
- [x] Update architecture specs to move API retry + schema retry into PydanticAI (Block must not manage either).
- [x] Add PydanticAI dependency; remove `instructor` and `tenacity` from `pyproject.toml`.
- [x] Implement PydanticAI-backed structured output path in `src/chaos/domain/llm_primitive.py`.
- [x] Remove tenacity wrappers and block-managed retry/repair behaviors for LLM API + schema failures.
- [x] Remove the internal semantic repair loop in `LLMPrimitive`.
- [x] Unify recovery logic and remove dead code paths (including `PolicyHandler.retry` if unused).
- [x] Make stats/usage reflect actual attempts and selected model.
- [x] Add unit tests mocking PydanticAI for API retry and schema retry scenarios.
- [x] Run `uv run pytest` and confirm coverage >= 95%.

## References
- [PydanticAI Migration Plan](pydanticai-migration-plan.md)
