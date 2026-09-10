# Project Directives & Autonomous Operating Rules

This project operates in **dual-capability development mode**:
1. **Interactive Mode**: Brainstorming, architectural planning, and feature scoping with the human author.
2. **Autonomous Ralph Loop Mode**: Ephemeral execution cycles advancing [ROADMAP.md](ROADMAP.md) autonomously.

---

## Autonomous Execution Rules
1. **Boot**: Read [MANIFESTO.md](MANIFESTO.md), [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md), and [AGENT_LOG.md](AGENT_LOG.md).
2. **Circuit Breakers**: If `BLOCKED.md` exists, stop immediately. Never hallucinate fake credentials if an external API key is strictly required.
3. **Priority Checks**:
   - Priority 1: Check for open bug reports via `python3 tools/issues.py check`. If found, fix with regression test first!
   - Cadence: If `run_number % 5 == 0`, execute a Senior Product Manager Meta-Improvement Sprint.
4. **Hermetic Verification**: Run `python3 tools/doctor.py`. 100% tests must pass before completing your cycle.
5. **No Ambiguity Delays**: Make decisions aligned with [MANIFESTO.md](MANIFESTO.md) and record ADR in [DECISIONS.md](DECISIONS.md).
6. **Handoff & Briefing**: Update `ROADMAP.md`, append to `AGENT_LOG.md`, deliver Human Executive Briefing.
7. **Mandatory Post-Briefing Promotion**: If any brainstormed idea is rated Rank **A+**, immediately append to `IDEAS.md` and commit before terminating.
