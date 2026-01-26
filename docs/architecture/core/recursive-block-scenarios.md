# Recursive Block Scenarios

## Status
Draft

## Purpose
Provide example flows that illustrate success, correction, and bubble-up behavior.

## Scope
Scenario narratives and high-level flow diagrams.

## Contents

### Scenario A: The Happy Path
User asks for weather; the manager orchestrates a single tool-backed block.

```text
[User] -> (Request) -> [RootContainer (Manager)]
                           |
                           +-> (1. Prepare) -> [WeatherBlock (Atomic)]
                           |                        |
                           |                        +-> Executes Tool
                           |                        +-> Returns SUCCESS ("20C")
                           |
                           +-> (2. Update Ledger)
                           +-> (3. Return) -> SUCCESS ("The weather is 20C")
```

### Scenario B: The Correction Loop (Internal Handling)
Weather tool fails because city name is typo'd. Manager repairs input and retries.

```text
[RootContainer (Manager)]
    |
    +-> (1. Execute) -> [WeatherBlock] (Input: "Lndn")
    |                       |
    |                       +-> Returns FAILURE (Reason: "City not found")
    |
    +-> (2. Catch) -> Manager checks Policy("CityNotFound") -> Strategy: LLM_PATCH
    |
    +-> (3. Patch) -> Manager calls Helper LLM ("Fix 'Lndn' for weather")
    |                 Helper returns "London"
    |
    +-> (4. Retry) -> [WeatherBlock] (Input: "London")
    |                       |
    |                       +-> Returns SUCCESS ("15C")
    |
    +-> (5. Return) -> SUCCESS
```

### Scenario C: The Bubble Up
Weather tool fails because API key is missing. Manager cannot fix this and bubbles.

```text
[RootContainer (Manager)]
    |
    +-> (1. Execute) -> [WeatherBlock]
    |                       |
    |                       +-> Returns FAILURE (Reason: "Auth Missing")
    |
    +-> (2. Catch) -> Manager checks Policy("AuthError") -> Strategy: BUBBLE
    |
    +-> (3. Abort) -> Manager returns FAILURE (Reason: "Auth Missing")
```

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
