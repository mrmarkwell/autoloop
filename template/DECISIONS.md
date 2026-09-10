# Architectural Decision Records (ADRs)

This document is an append-only log of significant design, architecture, and technology decisions made by developers and autonomous agents. When faced with ambiguity or multiple viable paths, evaluate options against [MANIFESTO.md](MANIFESTO.md), make the decision, and record it here.

---

## ADR-001: Autonomous Agent Development Protocol ("The Ralph Loop")
- **Date**: Seed Initialized
- **Status**: Accepted
- **Context**: The project is designed to be developed, maintained, and self-improved by autonomous agents with near-zero manual code oversight. Without a disciplined operating protocol, agents risk losing context across turns, accumulating debt, or stalling on minor ambiguities.
- **Decision**:
  1. Adopt the Ralph Loop lifecycle: Boot → Priority Triage → Cadence Check → Implement & Verify → Log Progress → Commit Checkpoint → Self-Terminate.
  2. Treat documentation (`MANIFESTO.md`, `ROADMAP.md`, `DECISIONS.md`, `IDEAS.md`, `AGENT_LOG.md`) as distributed state machines.
  3. Resolve ambiguities autonomously without prompting the user, recording the engineering rationale in this document.
  4. Real blockers (missing external credentials or physical barriers) are recorded in `BLOCKED.md` to halt execution safely.
- **Consequences**:
  - Agents remain fully autonomous and unblocked.
  - Complete traceability of architectural rationale.
  - Human stakeholders review progress retrospectively via Executive Briefings.

---

## ADR-002: Living Documentation State Machines
- **Date**: Seed Initialized
- **Status**: Accepted
- **Context**: Autonomous agents require a reliable, human-readable, machine-parseable institutional memory that survives ephemeral process restarts and avoids context window bloat.
- **Decision**:
  - `ROADMAP.md` is the declarative backlog and task queue.
  - `AGENT_LOG.md` is the sequential chronological execution log.
  - `DECISIONS.md` records all architectural compromises and invariants.
  - `IDEAS.md` is the intake hopper for brainstormed concepts with explicit letter grades.
  - `doctor.py` enforces state-machine synchronization across these documents before every commit.
- **Consequences**:
  - Eliminates context drift and contradiction across agent runs.
  - Provides a single source of truth for both humans and agents.

---

## ADR-003: Continuous Hermetic Verification Contract
- **Date**: Seed Initialized
- **Status**: Accepted
- **Context**: Code produced autonomously must be provably correct, reproducible, and safe. Flaky, slow, or unverified code degrades the autonomous loop.
- **Decision**:
  1. Every code change must be accompanied by unit tests.
  2. All tests must be fast, deterministic, and runnable hermetically via the project's verification suite.
  3. Pre-commit and pre-push hooks (`tools/doctor.py`) enforce 100% test pass before changes are committed or submitted.
- **Consequences**:
  - High velocity and confidence during autonomous iterations.
  - Immediate detection of regressions.
