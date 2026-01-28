# Recursive Block Scenarios

## Status
Draft

## Purpose
Provide example flows that illustrate success, correction, and bubble-up behavior.

## Scope
Scenario narratives and high-level flow diagrams.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Scenario A: The Happy Path
User asks for weather; a composite block orchestrates a single tool-backed block.

```text
[User] -> (Request) -> [RootBlock (Composite)]
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
Weather tool fails because city name is typo'd. The calling block repairs input and retries.

```text
[RootBlock (Composite)]
    |
    +-> (1. Execute) -> [WeatherBlock] (Input: "Lndn")
    |                       |
    |                       +-> Returns FAILURE (error_type: CityNotFoundError, reason: "city_not_found")
    |
    +-> (2. Catch) -> RootBlock checks recovery policy for the failure
    |
    +-> (3. Patch) -> RootBlock executes a helper block to repair input ("Fix 'Lndn' for weather")
    |                 Helper returns "London"
    |
    +-> (4. Retry) -> [WeatherBlock] (Input: "London")
    |                       |
    |                       +-> Returns SUCCESS ("15C")
    |
    +-> (5. Return) -> SUCCESS
```

### Scenario C: The Bubble Up
Weather tool fails because API key is missing. The calling block cannot fix this and bubbles.

```text
[RootBlock (Composite)]
    |
    +-> (1. Execute) -> [WeatherBlock]
    |                       |
    |                       +-> Returns FAILURE (error_type: AuthError, reason: "auth_missing")
    |
    +-> (2. Catch) -> RootBlock checks recovery policy for the failure -> Strategy: Bubble
    |
    +-> (3. Abort) -> RootBlock returns FAILURE (error_type: AuthError, reason: "auth_missing")
```

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Architecture Index](../index.md)
