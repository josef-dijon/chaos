# Block Execution Semantics

## Status
Draft

## Purpose
Define deterministic execution semantics for leaf and composite blocks so independent implementations behave the same under success, failure, and recovery.

## Scope
Block state machine expectations, composite graph execution algorithm, transition evaluation rules, and safety limits.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Block State Machine
`BlockState` is a minimal execution guard. It is not an external scheduling API.

Allowed states:
- `READY`: block is idle.
- `BUSY`: block is executing.
- `WAITING`: execution cannot continue without an explicit recovery/resume action.

Requirements:
- A block attempt MUST transition `READY -> BUSY` at the start of `execute`.
- A block attempt MUST eventually leave `BUSY` and end in `READY` unless it enters `WAITING`.
- The detailed meaning of `WAITING` is intentionally unresolved; see [Block Architecture Open Questions](block-open-questions.md).

### Composite Graph Model
A composite block owns a graph with:
- `nodes`: mapping of `node_name -> block`
- `entry_point`: `node_name`
- `transitions`: mapping of `node_name -> transition`

Transition forms:
- Linear transition: a single `target` node name.
- Branching transition: an ordered list of branches.

Branch form:
- `condition`: a condition identifier.
- `target`: the target node name.

Determinism requirements:
- Branches MUST be evaluated in a deterministic order.
- If branching is used, evaluation MUST be first-match.
- Branching transitions SHOULD include a final default branch.

### Graph Validation
Composites MUST validate their graph definition before execution begins.

Minimum validation:
- `entry_point` MUST exist in `nodes`.
- Every transition target MUST exist in `nodes`.
- Branching transitions SHOULD include a default branch; if omitted, the "no branch matched" case MUST be handled deterministically.

Failure behavior:
- If validation fails, the composite MUST return a failed `Response`.

### Standard Failure Reasons (Composite Runtime)
If a composite cannot proceed due to graph/runtime constraints, it SHOULD use stable `reason` labels so failures are understandable after serialization.

Recommended `reason` values:
- `invalid_graph`
- `unknown_node`
- `no_transition`
- `max_steps_exceeded`
- `condition_resolution_error`

### Condition Resolution
Conditions are predicates used by a composite to choose the next node.

Requirements:
- A condition identifier MUST resolve to an executable predicate during graph construction.
- If a condition identifier cannot be resolved, graph construction MUST fail (fail-fast).
- Condition evaluation MUST be side-effect free.

Note: The architecture does not mandate how conditions are referenced (string-keyed registry vs direct callables). It mandates validation and deterministic evaluation.

### Safety Limits
Composite execution MUST be bounded to prevent infinite loops.

Requirements:
- A composite run MUST enforce a maximum step count (`max_steps`).
- If `max_steps` is exceeded, the composite MUST return a failed `Response`.

Recommended defaults:
- `max_steps = 128`

### Reference Algorithm (Composite Execution)
This is a normative reference algorithm. Implementations MAY differ internally but MUST preserve the same externally observable behavior.

Pseudocode:

```text
execute_composite(root_request):
  current = entry_point
  steps = 0

  while True:
    steps += 1
    if steps > max_steps:
      return Response(
        success=False,
        reason="max_steps_exceeded",
        details={"max_steps": max_steps},
        error_type=Exception
      )

    child = nodes[current]
    child_request = build_child_request(
      parent_request=root_request,
      node_name=current,
      child_block=child,
      attempt=1
    )

    result = execute_with_recovery(child, child_request)

    if result.success() is False:
      return synthesize_failure(result)

    # Success
    maybe_update_state_from_success(current, result)

    transition = transitions.get(current)
    if transition is None:
      return synthesize_success(result)

    next_node = choose_next_node(transition, result)
    if next_node is None:
      return Response(
        success=False,
        reason="no_transition",
        details={"node": current},
        error_type=Exception
      )

    current = next_node
```

### Transition Selection
`choose_next_node` MUST behave as follows:

- For a linear transition, return the configured target node.
- For a branching transition, evaluate branches in order and return the target of the first branch whose condition is true.
- If no branch matches, return `None`.

### Child Request Construction
Composite blocks MUST construct child requests in a way that preserves traceability and supports retries/repairs.

Requirements:
- `context` MUST be pruned to the minimum required for the child.
- Metadata propagation SHOULD follow [Block Request and Metadata](block-request-metadata.md).

### Notes on Ledger Integration
This document does not define ledger mutation/commit semantics. It defines execution flow and determinism.

Ledger design and open questions:
- [State Ledger](03-state-ledger.md)
- [Block Architecture Open Questions](block-open-questions.md)

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Responses](block-responses.md)
- [Block Recovery Semantics](block-recovery-semantics.md)
- [Block Tool and Side-Effect Safety](block-tool-safety.md)
- [Block Observability](block-observability.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [State Ledger](03-state-ledger.md)
- [Architecture Index](../index.md)
