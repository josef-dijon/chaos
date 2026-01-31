# PydanticAI Migration Checklist

## Status
Draft

## Contents
- [ ] Update architecture specs to move API retry + schema retry into PydanticAI (Block must not manage either).
- [ ] Add PydanticAI dependency; remove `instructor` and `tenacity` from `pyproject.toml`.
- [ ] Implement PydanticAI-backed structured output path in `src/chaos/domain/llm_primitive.py`.
- [ ] Remove tenacity wrappers and block-managed retry/repair behaviors for LLM API + schema failures.
- [ ] Remove the internal semantic repair loop in `LLMPrimitive`.
- [ ] Unify recovery logic and remove dead code paths (including `PolicyHandler.retry` if unused).
- [ ] Make stats/usage reflect actual attempts and selected model.
- [ ] Add unit tests mocking PydanticAI for API retry and schema retry scenarios.
- [ ] Run `uv run pytest` and confirm coverage >= 95%.

## References
- [PydanticAI Migration Plan](pydanticai-migration-plan.md)
