# SOP Agent Node: Architecture & Philosophy

This document outlines the high-fidelity, sovereign SOP (Standard Operating Procedure) Agent Node architecture developed for reliable, granular agentic workflows.

## 1. Core Philosophy: The "Sovereign Microservice"
The Agent Node is treated as an encapsulated, stateful microservice. It hides internal complexity from the parent graph, exposing only two states and two output types. This ensures **atomic transactions** and **deterministic autonomy**.

- **Internal Complexity:** Multi-step loops, tool calls, and skill loading.
- **External Simplicity:** Input (Request) -> Output (Success Payload OR Clarification Schema).

---

## 2. Node State Machine
The parent graph must respect the node's current state to maintain transactional integrity.

| State | Description | Parent Constraint |
| :--- | :--- | :--- |
| **READY** | Idle or just completed a mission. | Accepting a new `NEW_REQUEST`. |
| **WAITING** | Suspended; awaiting human/external input. | Accepting only `CLARIFICATION_RESPONSE`. |

---

## 3. Internal Block Definitions

### A. DECOMPOSITION
- **Purpose:** Intent extraction and task splitting.
- **Logic:** Breaks a "messy" user query into atomic, parallelizable **Tracks**.
- **Philosophy:** Atomic tasks are easier to validate and execute than complex ones.

### B. QUERY REFINEMENT (The Planning Loop)
- **Purpose:** Recursive refinement of the mission blueprint.
- **Logic:** 
    1. **Detection:** Identifies missing structural parameters or ambiguities in each track.
    2. **The Gap Filler:** If a gap can be filled via the **Tool & Skill Library** (e.g., fetching a user's default home city), it executes that tool and updates the track context.
    3. **External Escalation:** If a gap remains and no internal tool can solve it, it generates a **Clarification Schema** and the node enters the `WAITING` state.
- **Philosophy:** The "Preparation Phase." No heavy research or execution begins until the inputs for all tracks are 100% complete and unambiguous through recursive refinement.

### C. QUERY EXECUTION (The Execution Loop)
- **Purpose:** Parallel information gathering and action execution.
- **Logic:** 
    1. Once the RQR phase is satisfied, the **COLLATOR** spawns parallel **Tracks**.
    2. **Internal Track Autonomy:** Each track operates as its own autonomous **Tool-Use Loop**.
    3. **The Context Builder (Track Loop):**
        - **Inference:** The track's LLM analyzes the current track context.
        - **Decision:** The LLM decides to either call a tool, or finish (Validator).
        - **Capability Check:** If a gap is identified but no tool exists in the library to bridge it, the track MUST exit with `TRACK_ERROR`.
        - **Multi-Step Execution:** A track can perform a sequence of tool calls (e.g., `search_trains` -> `select_seat` -> `confirm_booking`) within its own isolated context.
- **Philosophy:** The "Work Phase." This is where the Tracks system divides and conquers. Each track is a "Mini-Agent" with a specific, guaranteed-complete mission.

subgraph Execution_Loop [Phase 2: Parallel Query Execution]
    direction TB
    StartQE[Start Parallel Tracks] --> T1[Track 1: Tool-Use Loop]
    StartQE --> T2[Track 2: Tool-Use Loop]
    StartQE --> TN[Track N: Tool-Use Loop]
    
    subgraph Track_Loop [Internal Track Logic]
        direction TB
        Inference[LLM Inference] --> Decision{Call Tool?}
        Decision -- "Yes" --> ToolExec[System Execution]
        ToolExec -- "Update Track Context" --> Inference
        Decision -- "Finish" --> Val{Validator}
        Val -- "Fail" --> Inference
        Val -- "Pass" --> FinalResult[Report to Collator]
    end
    
    T1 & T2 & TN --> Collator[Collator]
end

subgraph Execution_Loop [Phase 2: Parallel Query Execution]
    direction TB
    StartQE[Start Parallel Tracks] --> T1[Track 1: Loop]
    StartQE --> T2[Track 2: Loop]
    StartQE --> TN[Track N: Loop]
    
    subgraph Track_Loop [Internal Track Logic]
        direction TB
        CB[Context Builder] --> Val{Validator}
        Val -- "Fail / Retry" --> CB
        Val -- "Pass" --> Exec[Executor]
    end
    
    T1 & T2 & TN --> Collator[Collator]
end

    Querier --> ExitWait[/EXIT: WAITING + Schema/]
    Executor --> Collator[Collator]
    Collator --> Responder[Responder]
    Responder --> ExitReady[/EXIT: READY + Payload/]
```

---

## 6. Important Implementation Notes
- **Context Synthesis:** The node builds a "Clean Context" for the Executor. The Executor never sees the intermediate "mess" of the research loop.
- **Instructional Skills:** Skills are prompt augmentations used within the current loop, whereas Sub-Agents are separate loops entirely.
- **Functional Atomicity:** The node acts like a database transaction—it either completes fully or provides a clear reason why it cannot.
