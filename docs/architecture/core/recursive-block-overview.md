# Recursive Block Overview

## Status
Draft

## Purpose
Summarize the core philosophy behind the recursive block architecture.

## Scope
Fractal design, self-similarity, and what it means for blocks to compose other blocks.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Core Philosophy: The Fractal Agent
The architecture of the CHAOS agent is built on a fractal design pattern. The system is composed of self-similar units called blocks.

- Self-similarity: A complex workflow looks the same externally as a primitive unit.
- Composition: A `Block` may contain and orchestrate other blocks.
- Unified interface: Every component adheres to the same `Block` interface.

### Design Implications
- Composition over wiring: blocks define execution logic and data flow.
- Explicit recovery: outcomes are handled via response + policy, not exceptions.
- Testability: small blocks with clear inputs and outputs reduce system coupling.

This enables infinite nesting and a simpler mental model focused on recursive blocks.

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Architecture Index](../index.md)
