# Container Manager Orchestration

## Status
Draft

## Purpose
Describe the container-as-manager orchestration pattern and hub-and-spoke flow.

## Scope
Manager control loop, response dispatch, and benefits of centralized context control.

## Contents

### The Manager Pattern (Containers)
In this architecture, the container is the manager. A `ContainerBlock` is a hub-and-spoke orchestrator that mediates transactions between children.

#### The Hub-and-Spoke Flow
1. Prepare: Manager reads ledger, applies pruning, and creates the `Request` for Child A.
2. Execute: Manager calls `ChildA.execute(request)` and waits.
3. Receive: Child A returns an `IResponse`.
4. Process (type-based dispatch):
   - SuccessResponse: update ledger and decide next step.
   - FailureResponse: execute policy and follow strategy chain.

#### Manager Responsibilities
- Construct and prune requests for each child.
- Translate child outputs into the next child inputs.
- Enforce policy selection and escalation behavior.
- Persist ledger updates and checkpoint boundaries.

#### Benefits
- Explicit handling: every outcome type has a policy definition.
- Context control: children only see what the manager allows.
- Dependency injection: manager maps Child A output to Child B input.

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
