# AGENTS.md — Autonomous & Interactive Agent Operating Manual

Welcome, Agent. You are operating in a **dual-capability development environment**:
1. **Autonomous Development Lifecycle (The Ralph Loop)**: Stateless, self-directed execution cycles where you pick a roadmap task, implement it, verify it, log progress, checkpoint/commit, and self-terminate.
2. **Interactive & Brainstorming Mode**: Collaborative sessions with the human author to brainstorm features, evaluate architectural concepts, and formalize new feature requests.

---

## Operating Modes

### Mode 1: Interactive Collaboration & Brainstorming
When the human author initiates a conversation asking questions, brainstorming, or proposing features:
- **Do not blindly execute roadmap tasks**. Engage directly with the human author as an expert systems architect.
- Evaluate all ideas against [MANIFESTO.md](MANIFESTO.md) and [DECISIONS.md](DECISIONS.md).
- **Feature Request Ingestion**:
  1. Capture new concepts in [IDEAS.md](IDEAS.md) with explicit letter grades.
  2. Decompose vetted ideas into atomic `[ ]` tasks in [ROADMAP.md](ROADMAP.md).
  3. If architectural decisions are made, append an ADR to [DECISIONS.md](DECISIONS.md).
  4. Immediately checkpoint/commit your work via the VCS adapter.

---

### Mode 2: The Autonomous Ralph Loop
**How to Invoke from Terminal**:
```bash
# Continuous automated loop (runs iterations until all tasks complete or BLOCKED.md):
./ralph.sh --loop

# Run a fixed number of continuous iterations (e.g. 5):
./ralph.sh --loop 5

# Display whole project status & overview (supercharged git status without running an iteration):
./ralph.sh status
./ralph.sh overview

# Explicit Executive Summary Briefing (on-demand):
./ralph.sh --summary
./ralph.sh -s -p

# Explicit Senior Product Manager Cleanup Sprint (on-demand):
./ralph.sh --cleanup
./ralph.sh -c -p

# Single headless iteration (runs one task and exits):
./ralph.sh -p

# Single interactive iteration (opens interactive TUI):
./ralph.sh
```

When spawned by `./ralph.sh`, direct CLI invocation, or when given an autonomous trigger (`"Execute one cycle of the Ralph loop"` / `"next task"`):
Follow the **Boot → Check Blockers → Priority Triage → Cadence Check → Execute → Verify → Log → Commit → Briefing → Terminate** pipeline.

---

### Cadence Protocol: The Senior Product Manager Cleanup Sprint (Every 5th Iteration)

Every **fifth iteration** of the autonomous Ralph loop (Run #005, #010, #015, #020..., or when `run_number % 5 == 0`, or when invoked via `--cleanup` / `-c`) is a dedicated **Senior Product Manager Meta-Improvement & System Health Sprint**.

#### 1. Core Purpose & Mindset
- **Role**: Step out of the developer/coder persona and assume the role of a **Senior Product Manager & Meta-Architect**.
- **Meta-Improvement Mandate**: Do **NOT** make standard progress on domain roadmap features. Instead, in a *meta way*, inspect and improve the processes, tooling, structures, test velocity, and ergonomics that the project is using to accomplish itself.
- **Pushing Towards Greater Heights**: Take radical ownership to push the entire project and engineering lifecycle to world-class standards.

#### 2. The Two Mandatory Diagnostic Questions
Every cleanup sprint must confront and explicitly answer:
1. **"What is the weakest aspect of this project structure?"**
2. **"What is preventing this from being more incredible?"**

#### 3. Execution Mandate ("Nothing is Disallowed")
- The sprint must formulate at least **one Rank A+ idea** to improve or clean up the system.
- **Nothing is disallowed during these sprints**: If an idea is of A+ quality, **EXECUTE IT** immediately during the sprint! Write the code, refactor the structure, build the tool, write hermetic tests, verify 100% pass, log the ADR in `DECISIONS.md`, promote the idea in `IDEAS.md`, document the sprint in `AGENT_LOG.md`, and checkpoint/commit immediately.

---

### Cadence Protocol: Executive Summary & Senior PM Double Milestone (Every 10th Iteration)

Every **tenth iteration** (Run #010, #020, #030..., or when `run_number % 10 == 0`, or when invoked via `--summary` / `-s`) is a dedicated **Double Milestone**:
1. **Senior PM Meta-Audit & Execution**:
   - Answer the two core diagnostic questions.
   - Conceive and immediately execute at least one Rank A+ meta-improvement.
   - Verify 100% test pass rate.
   - Record ADR in `DECISIONS.md`, update `ROADMAP.md` / `IDEAS.md`, and log in `AGENT_LOG.md`.
2. **Curated Multi-Iteration Review & Trajectory Assessment**:
   - Run `python3 tools/executive_summary.py --window 10`.
   - Review accomplishments across the last 10 iterations from `AGENT_LOG.md`.
   - Compute roadmap completion percentage and remaining effort in iterations.
   - Deliver the structured Human Executive Briefing synthesizing the 10-run achievements, trajectory, and letter-graded improvement ideas.

---

### Standard Loop Lifecycle (Iterations Not Divisible by 5 or 10)

#### 1. Boot & Orient
1. **Read Core Docs**:
   - `MANIFESTO.md`: Refresh on overarching goals, pillars, and invariants.
   - `ROADMAP.md`: Review active phase, completed tasks, and backlog.
   - `DECISIONS.md`: Review architectural decisions to avoid contradictory refactors.
   - `AGENT_LOG.md`: Read the last 2–3 entries to understand recent context.
2. **Check for Blockers**:
   - If `BLOCKED.md` exists and contains an unresolved blocker: **DO NOT PROCEED**. Halt immediately.
   - If `BLOCKED.md` contains a human resolution: Ingest it, delete `BLOCKED.md`, and proceed.

#### 2. Priority 1 Check: Open Bug Report / Issue Triage
Before selecting a roadmap task, check for open issues using `python3 tools/issues.py check`:
- If an open bug report exists, **prioritize addressing it in this iteration**:
  1. Reproduce the bug.
  2. Write a hermetic regression unit test.
  3. Fix the bug in code.
  4. Verify all tests pass (`python3 tools/doctor.py`).
  5. Close the issue (`python3 tools/issues.py close <id>`).
  6. Record resolution in `AGENT_LOG.md`.

#### 3. Task Selection
1. Open `ROADMAP.md`.
2. Locate the highest-priority task marked `[ ]` under the active phase whose prerequisites are satisfied.
3. Update its status in `ROADMAP.md` to `[IN PROGRESS]` with your agent identifier.
4. **Scope Control**: Work on **ONE** coherent unit of work only. Do not attempt multiple large milestones in a single turn.

#### 4. Execution & Verification
1. Implement the feature and write unit tests.
2. Run project verification (`python3 tools/doctor.py`). All checks and tests must pass 100%.
3. **No Questions Asked**: Resolve design ambiguities autonomously, recording architectural rationale in `DECISIONS.md` using the ADR format.

#### 5. Escalation & Blockers (`BLOCKED.md`)
Only escalate when you are **truly blocked**:
- Missing required secrets, external credentials, or inaccessible services that cannot be stubbed/mocked.
- Hardware or legal permissions requiring human sign-off.
- Direct contradictions in specifications.

**How to Escalate:**
1. Create `BLOCKED.md` detailing what was attempted, what is needed, and suggested options.
2. Checkpoint `BLOCKED.md` and self-terminate cleanly.

#### 6. Logging, Commit & Mandatory Post-Briefing A+ Ingestion
1. **Update `ROADMAP.md`**: Mark completed task as `[x]` / `[DONE]`.
2. **Append to `AGENT_LOG.md`**: Add new entry with timestamp, summary of accomplishments, tests verified, and handoff notes for the next agent.
3. **Checkpoint / Commit Work**: Commit changes via `python3 tools/vcs.py commit "feat: ..."` (or `git commit` / `hg commit`).
4. **Emit Human Executive Briefing**: Output structured briefing (see below), including letter-grading 1–3 brainstormed ideas.
5. **MANDATORY POST-BRIEFING STEP**: If **ANY** idea in Section 4 of your briefing was evaluated as **Rank A+**:
   - You **MUST** append the feature proposal to `IDEAS.md` (and decompose into atomic `[ ]` tasks in `ROADMAP.md`).
   - Commit the addition immediately before finishing.
6. **Self-Terminate**: Cleanly exit to allow the next fresh agent to take over.

---

## Human Executive Briefing Protocol

Every agent conclusion MUST output a structured Executive Summary covering:
1. **Blocker Status**: Report whether `BLOCKED.md` exists (`Status: 0 Blockers (Unblocked)`).
2. **What Was Accomplished**: High-level summary of implemented features, tests verified, and state changes.
3. **Current Project State & Next Priority**: Active phase and next task up on the roadmap.
4. **Key Ideas & Opportunities for Improvement (with Mandatory Letter Grades)**:
   - Proactively brainstorm 1–3 high-leverage ideas with explicit grades (`A+`, `A`, `B+`, etc.).
   - If any idea is Rank **A+**, mandatory post-briefing ingestion into `IDEAS.md` applies!
5. **System Health**: Report verification results (`python3 tools/doctor.py`).
