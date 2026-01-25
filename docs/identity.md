# Identity Schema Guide

## Purpose
The identity file is the persistent, schema-validated definition of an agent. It
anchors the agent's role, values, instructions, memory behavior, and capability
access rules.

This document describes each identity parameter, how it is used to tune the
agent, and the weighting system that tells the subconscious how careful it must
be with changes.

## Masked Schema and Masked Identity
The subconscious must only see a masked view of the identity and its schema.
Masking uses the tuning policy (plus an implicit blacklist) to remove forbidden
paths entirely.

- The masked identity is produced by `Identity.get_masked_identity()`.
- The masked schema is produced by `Identity.get_tunable_schema()`.
- Any field that is blacklisted is not present in the masked views.
- Parent-path allow rules expose all descendant fields unless blocked.

This ensures the subconscious can only propose updates for paths it is allowed
to tune.

## Weighting System
Each field includes a `weight` (1-10) in the JSON schema:

- **10 (Critical):** Core identity, loop behavior, safety, or config integrity.
- **7-9 (High):** Strongly stabilizing fields; changes should be rare and deliberate.
- **4-6 (Moderate):** Adjust with care, but tuning is plausible.
- **1-3 (Mutable):** Intended for frequent adaptation.

The subconscious should be more conservative with higher weights.

## Identity Parameters
Paths are listed as dot-separated keys. Weights are shown in parentheses.

### Root
- `schema_version` (10): Schema compatibility marker. Never tuned.
- `profile` (9): The identity profile (name, role, core values).
- `instructions` (8): System prompts and tunable operational notes.
- `loop_definition` (10): Selects the reasoning loop. Never tuned.
- `tool_manifest` (6): Legacy allowed tool list (overridden by tool_whitelist).
- `memory` (8): Memory configuration for actor and subconscious.
- `tuning_policy` (10): Declares what the subconscious may modify.
- `skills_whitelist` (7): Allowed skills. Null means all.
- `skills_blacklist` (7): Forbidden skills.
- `knowledge_whitelist` (7): Allowed knowledge domains. Null means all.
- `knowledge_blacklist` (7): Forbidden knowledge domains.
- `tool_whitelist` (7): Allowed tools. Null means all.
- `tool_blacklist` (7): Forbidden tools.

### Profile
- `profile.name` (6): Display name used in prompts.
- `profile.role` (9): Primary role; anchors task framing.
- `profile.core_values` (9): High-stability values guiding behavior.

### Instructions
- `instructions.system_prompts` (8): Base system prompts; change carefully.
- `instructions.operational_notes` (2): Primary tunable behavior adjustments.

### Memory (Implicitly Blacklisted)
These paths are implicitly blacklisted and never shown to the subconscious:

- `memory.actor`
- `memory.subconscious`

They remain part of the identity schema for human operators and system use.

### Memory Persona Configuration
- `memory.<persona>.ltm_collection` (9): LTM collection name. Keep stable.
- `memory.<persona>.stm_window_size` (6): STM window size (loops).
- `memory.<persona>.stm_search` (7): STM search tuning settings.

### STM Search
- `memory.<persona>.stm_search.engine` (6): STM search engine identifier.
- `memory.<persona>.stm_search.algorithm` (6): STM search algorithm name.
- `memory.<persona>.stm_search.threshold` (7): Similarity threshold (0-100).
- `memory.<persona>.stm_search.top_k` (6): Maximum results per query.
- `memory.<persona>.stm_search.recency_half_life_seconds` (7): Recency decay.
- `memory.<persona>.stm_search.weights` (7): Scoring weights.

### STM Search Weights
- `memory.<persona>.stm_search.weights.similarity` (7): Similarity weight.
- `memory.<persona>.stm_search.weights.recency` (7): Recency weight.
- `memory.<persona>.stm_search.weights.kind_boosts` (6): Boosts per event kind.
- `memory.<persona>.stm_search.weights.visibility_boosts` (6): Boosts per visibility.

### Tuning Policy (Implicitly Blacklisted)
The tuning policy is blacklisted from subconscious access and only managed by
human operators.

- `tuning_policy.whitelist` (9): Allowed dot-paths for tuning (parent scopes apply).
- `tuning_policy.blacklist` (9): Forbidden dot-paths (overrides whitelist).

## Tuning Policy Rules
- Paths use dot-separated keys.
- Parent paths cover all children (e.g., `instructions` covers `instructions.system_prompts`).
- Blacklist entries always win, even if whitelisted.
- The system enforces an implicit blacklist:
  `schema_version`, `tuning_policy`, `memory.subconscious`, `memory.actor`,
  `loop_definition`.
