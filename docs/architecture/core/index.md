# Core Architecture

## Overview
Foundational primitives and block-based architecture imported from the core architecture specification.

## Index
- [Recursive Block Overview](recursive-block-overview.md): Fractal design and recursive block model.
- [Block Glossary](block-glossary.md): Shared vocabulary for block execution, recovery, and ledger semantics.
- [Block Architecture](block-interface.md): What a block is and how it executes (leaf + composite).
- [Block Request and Metadata](block-request-metadata.md): Canonical request envelope and reserved metadata keys.
- [Block Execution Semantics](block-execution-semantics.md): Deterministic composite graph execution and transition rules.
- [Block Responses](block-responses.md): Polymorphic response semantics.
- [Recovery Policy System](recovery-policy-system.md): Recovery policies and escalation chain.
- [Block Recovery Semantics](block-recovery-semantics.md): Deterministic application of recovery policies.
- [Block Tool and Side-Effect Safety](block-tool-safety.md): Retry/rollback rules for side effects.
- [Block Observability](block-observability.md): Trace/span model and event vocabulary.
- [Block Estimation](block-estimation.md): Estimation contract and BlockEstimate schema.
- [Block Testing Guidelines](block-testing-guidelines.md): Deterministic unit testing patterns.
- [Block Architecture Open Questions](block-open-questions.md): Unresolved decisions that must be specified before runtime behavior is normative.
- [LLM Primitive](02-llm-primitive.md): The atomic unit of LLM interaction and validation.
- [State Ledger](03-state-ledger.md): Context, provenance, and checkpoint/rollback design.
- [Recursive Block Scenarios](recursive-block-scenarios.md): Example flows and failure handling.
- [Core Architecture Overview (Legacy)](core-architecture.md): Historical context; not normative.
- [Archive](../../archive/index.md): Historical notes and artifacts.

## Roadmap
- None yet.

| Item | Status | Notes |
| --- | --- | --- |
| TBD | planned | Core roadmap pending. |

## Related
- [Architecture Index](../index.md)
- [Documentation Standard](../../documentation-standard.md)
