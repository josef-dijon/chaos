# Block Estimation Checklist

## Status
Draft

## Contents
- [ ] Define `BlockEstimate` schema + cold-start semantics.
- [ ] Add `estimate_execution` to the Block interface.
- [ ] Add block stats recording/query interfaces with JSON/in-memory backend.
- [ ] Implement `LLMPrimitive.estimate_execution` with stats adapter.
- [ ] Update architecture docs to reflect estimation contracts.
- [ ] Add/adjust unit tests; keep coverage >= 95%.
- [ ] Run `uv run pytest`.

## References
- [Block Estimation Plan](block-estimation-plan.md)
