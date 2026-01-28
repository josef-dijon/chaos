# Block Recovery Semantics

## Status
Draft

## Purpose
Define how recovery policies are selected and applied so callers recover from child failures deterministically.

## Scope
Policy selection, policy application order, attempt accounting, and reference algorithms for retry/repair/debug/bubble.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Selection: From Failure to Policy Stack
When a child returns a failed `Response`, the caller determines the child recovery strategy by requesting a policy stack:

- Call `child.get_policy_stack(error_type)` where `error_type` is the failure classification.
- The returned policy stack MUST be treated as ordered.

Notes:
- The canonical selector is `error_type` (see [Block Responses](block-responses.md)).
- If `error_type` is missing or unusable after serialization, the caller SHOULD still have a deterministic mapping strategy (for example: map from `reason`).

### Policy Application Order
Given an ordered policy stack:

- The caller MUST attempt policies in order.
- A policy attempt MAY execute the child block one or more times (for example: retry up to N attempts).
- If a policy yields a successful `Response`, recovery stops and the success is returned.
- If a policy yields a failed `Response` and is exhausted, the caller proceeds to the next policy.
- If all policies are exhausted, the caller MUST return a failed `Response`.

### Attempt Accounting
Recovery requires stable attempt tracking.

Requirements:
- Each child attempt MUST increment an attempt counter scoped to the same child and node within a composite run.
- The attempt counter SHOULD be recorded in request/response metadata as `attempt`.

Recommended rules:
- Attempt numbering is 1-based.
- Attempt increments on each re-execution caused by retry or repair.

See:
- [Block Request and Metadata](block-request-metadata.md)

### Standard Policies (Behavior)

#### RetryPolicy
Intent: re-execute the same block with the same request.

Requirements:
- Retry MUST preserve `payload` and `context`.
- Retry MUST generate a new `span_id` per attempt.
- Retry MUST obey side-effect safety constraints (retry is forbidden for non-idempotent attempts).

See:
- [Block Tool and Side-Effect Safety](block-tool-safety.md)

Backoff:
- If the policy config includes a delay, the caller SHOULD delay between attempts.
- Delay SHOULD support jitter to avoid thundering herds.

#### RepairPolicy
Intent: transform the request (typically the payload and/or context) and retry.

Requirements:
- Repair MUST produce a new `Request`.
- Repair MUST be deterministic given `(request, failure)`.
- Repair MUST NOT mutate the original request in place.
- Repair MUST obey side-effect safety constraints.

See:
- [Block Tool and Side-Effect Safety](block-tool-safety.md)

#### DebugPolicy
Intent: perform a deeper diagnostic pass (for example: checkpoint/rollback and state patching).

Requirements:
- Debug MUST preserve the original failure context.
- Debug MAY create a checkpoint and rollback as part of its process.
- Debug MUST treat rollback as ledger-only; external side effects are not undone.

Ledger linkage:
- [State Ledger](03-state-ledger.md)

#### BubblePolicy
Intent: stop attempting local recovery and return the failure to the caller.

Requirements:
- Bubble MUST return a failed `Response`.
- Bubble SHOULD preserve provenance (original reason/details) rather than replacing it.

### Reference Algorithm (Execute With Recovery)
This is a normative reference algorithm.

```text
execute_with_recovery(child, initial_request):
  attempt = 1
  response = child.execute(with_attempt(initial_request, attempt))

  if response.success() is True:
    return response

  policies = child.get_policy_stack(error_type=response.error_type)

  for policy in policies:
    if policy is BubblePolicy:
      return response

    if policy is RetryPolicy:
      for i in 1..policy.max_attempts:
        attempt += 1
        maybe_sleep(policy, attempt)
        response = child.execute(with_attempt(initial_request, attempt))
        if response.success() is True:
          return response
      continue

    if policy is RepairPolicy:
      repaired_request = apply_repair(policy, initial_request, response)
      attempt += 1
      response = child.execute(with_attempt(repaired_request, attempt))
      if response.success() is True:
        return response
      continue

    if policy is DebugPolicy:
      response = run_debug(policy, initial_request, response)
      if response.success() is True:
        return response
      continue

  return response
```

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Responses](block-responses.md)
- [Recovery Policy System](recovery-policy-system.md)
- [State Ledger](03-state-ledger.md)
- [Block Tool and Side-Effect Safety](block-tool-safety.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [Architecture Index](../index.md)
