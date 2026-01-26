# Recursive Block Overview

## Status
Draft

## Purpose
Summarize the core philosophy behind the recursive block architecture.

## Scope
Fractal design, self-similarity, and the container-as-manager concept.

## Contents

### Core Philosophy: The Fractal Agent
The architecture of the CHAOS agent is built on a fractal design pattern. The system is composed of self-similar units called blocks.

- Self-similarity: A complex workflow looks the same externally as a primitive unit.
- The container is the manager: A `ContainerBlock` is an active runtime engine that orchestrates its children.
- Unified interface: Every component adheres to the same `IBlock` interface.

### Design Implications
- Composition over wiring: containers define execution logic and data flow.
- Explicit recovery: outcomes are handled via response + policy, not exceptions.
- Testability: small blocks with clear inputs and outputs reduce system coupling.

This enables infinite nesting and a simpler mental model focused on recursive containers.

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
