#!/usr/bin/env bash
set -euo pipefail

# ralph.sh — Universal Autonomous & Interactive Development Loop Runner
# Invokes LLM Agent CLI directly in terminal with auto-approved permissions.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

JETSKI_CLI="/google/bin/releases/jetski-devs/tools/cli"
DEFAULT_PROMPT="Execute one cycle of the Ralph loop per AGENTS.md."

CLEANUP_PROMPT="Execute one cycle of the Ralph loop per AGENTS.md.

MANDATORY CADENCE: Senior Product Manager Meta-Improvement & System Health Sprint.

You are acting as a Senior Product Manager auditing the entire project structure and execution processes.
DO NOT make standard feature progress on domain roadmap tasks during this cycle.
Instead, focus on meta-improvements to how this project accomplishes itself.

Core Diagnostic Questions:
1. What is the weakest aspect of this project structure?
2. What is preventing this from being more incredible?

Requirements:
- Conduct an audit across: architecture, test velocity & hermeticity, build targets, harness automation, developer ergonomics, and documentation integrity.
- Formulate at least ONE Rank A+ idea to improve or clean up the system/processes.
- You have full ownership: NOTHING is disallowed. If your idea is A+ quality, EXECUTE IT completely during this cycle!
- Implement, test, and verify the improvement (100% test pass rate required).
- Record architectural decisions in DECISIONS.md (ADR) and promote the Rank A+ feature in IDEAS.md.
- Log your accomplishments in AGENT_LOG.md as a Senior PM Cleanup Sprint entry.
- Checkpoint / commit your work immediately via VCS adapter.
- Provide the structured Human Executive Briefing."

SUMMARY_PROMPT="Execute one cycle of the Ralph loop per AGENTS.md.

MANDATORY CADENCE: Senior Product Manager Meta-Improvement Sprint & 10th-Iteration Executive Briefing.

Every 10th iteration is divisible by 5 and represents a double milestone.
You are acting as a Senior Product Manager auditing the entire project structure and execution processes, followed by curating the 10-iteration Executive Summary.
DO NOT make standard feature progress on domain roadmap tasks during this cycle.

PART 1: SENIOR PRODUCT MANAGER META-IMPROVEMENT SPRINT
- Answer the Two Core Diagnostic Questions:
  1. What is the weakest aspect of this project structure?
  2. What is preventing this from being more incredible?
- Formulate at least ONE Rank A+ idea to improve or clean up the system/processes.
- You have full ownership: NOTHING is disallowed. If your idea is A+ quality, EXECUTE IT completely during this cycle!
- Implement, test, and verify the improvement (100% test pass rate required).
- Record architectural decisions in DECISIONS.md (ADR) and promote the Rank A+ feature in IDEAS.md.
- Log your accomplishments in AGENT_LOG.md as a Senior PM Cleanup Sprint entry.
- Checkpoint / commit your work immediately via VCS adapter.

PART 2: EXECUTIVE SUMMARY & TRAJECTORY BRIEFING
- Run the zero-dependency Executive Summary tool:
  python3 tools/executive_summary.py --window 10
- Review and curate the accomplishments across the last 10 iterations (from AGENT_LOG.md).
- Conclude your cycle by delivering the curated Human Executive Briefing covering:
  1. Blocker Status (BLOCKED.md)
  2. High-level trajectory overview (completion percentage, estimated remaining iterations to finish roadmap)
  3. 10-Iteration accomplishment review
  4. System health and architectural invariant verification (tests, doctor checks)
  5. Letter-graded improvement opportunities (with mandatory immediate promotion for any Rank A+ ideas)."

DEFAULT_TIMEOUT="30m"

# Helper: Detect the next run number from AGENT_LOG.md
get_next_run_number() {
    local last_run
    last_run=$(grep -oE '\[Run [0-9]+\]' "$REPO_DIR/AGENT_LOG.md" 2>/dev/null | tail -n1 | grep -oE '[0-9]+' || echo "0")
    if [ -z "$last_run" ]; then
        last_run=0
    fi
    echo "$((10#$last_run + 1))"
}

is_summary_run() {
    local num="${1:-0}"
    if [ "$num" -gt 0 ] && [ $((num % 10)) -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

is_cleanup_run() {
    local num="${1:-0}"
    if [ "$num" -gt 0 ] && [ $((num % 5)) -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

show_help() {
    cat << 'HELP_EOF'
ralph.sh — Autonomous & Interactive Development Loop Runner

Usage:
  ./ralph.sh [OPTIONS] [PROMPT]

Operating Modes:
  (no args)             Launch single interactive session in terminal TUI (with auto-cadence detection)
  --print, -p           Launch single headless autonomous cycle with real-time streaming telemetry
  --loop, -l [N]        Run continuous autonomous loop (iterates until all tasks complete, BLOCKED.md, or N cycles)
  --cleanup, -c         Explicitly run a Senior Product Manager Meta-Improvement Sprint
  --summary, -s         Explicitly run a 10th-Iteration Executive Summary & Trajectory Briefing
  --help, -h            Show this help guide

Cadence Protocol:
  - Run # % 10 == 0:    Double Milestone: Senior PM Meta-Sprint + Executive Summary Briefing
  - Run # % 5 == 0:     Senior PM Meta-Improvement & System Health Sprint
  - Standard Runs:      Autonomous roadmap task execution

Examples:
  ./ralph.sh                     # Interactive single iteration (opens TUI)
  ./ralph.sh -p                  # Headless single iteration (streams progress and exits)
  ./ralph.sh --loop              # Continuous loop until completion
  ./ralph.sh --loop 5            # Continuous loop for 5 iterations
HELP_EOF
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    show_help
    exit 0
fi

if [ ! -x "$JETSKI_CLI" ]; then
    echo "Notice: Standard Jetski CLI binary not at $JETSKI_CLI. Trying PATH..."
    if command -v jetski >/dev/null 2>&1; then
        JETSKI_CLI="jetski"
    else
        echo "Error: LLM CLI binary not found. Please install or configure JETSKI_CLI." >&2
        exit 1
    fi
fi

# Continuous Loop Mode (--loop / -l)
if [ "${1:-}" = "--loop" ] || [ "${1:-}" = "-l" ]; then
    shift
    MAX_ITERATIONS=0
    if [ "$#" -gt 0 ] && [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
        shift
    fi

    echo "======================================================================"
    echo " Starting Continuous Ralph Loop"
    if [ "$MAX_ITERATIONS" -gt 0 ]; then
        echo " Max iterations: $MAX_ITERATIONS"
    else
        echo " Max iterations: Unlimited (until all tasks complete or BLOCKED.md)"
    fi
    echo " Repository:     $REPO_DIR"
    echo " Timeout/cycle:  $DEFAULT_TIMEOUT"
    echo " Press Ctrl+C at any time to exit safely."
    echo "======================================================================"

    ITERATION=1
    while true; do
        if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -gt "$MAX_ITERATIONS" ]; then
            echo ""
            echo " [✓] Reached target iteration count ($MAX_ITERATIONS). Exiting loop."
            break
        fi

        # Guardrail 1: Check for blocker escalation
        if [ -f "BLOCKED.md" ]; then
            echo ""
            echo " [!] BLOCKED.md detected. Halting loop to prevent spinning."
            echo "     Please resolve the blocker in BLOCKED.md, delete the file, and re-run."
            exit 1
        fi

        # Guardrail 2: Check for remaining roadmap tasks
        if ! grep -q '\[ \]' ROADMAP.md; then
            if python3 "$REPO_DIR/tools/issues.py" check --quiet 2>/dev/null; then
                echo ""
                echo " [!] All roadmap tasks completed, but open issue detected. Continuing loop to resolve."
            else
                echo ""
                echo " [✓] All roadmap tasks marked [x] / completed! Loop finished."
                break
            fi
        fi

        NEXT_RUN=$(get_next_run_number)
        CYCLE_PROMPT="$DEFAULT_PROMPT"
        SPRINT_BANNER="Standard Cycle (Roadmap Task Execution)"

        # Priority 1: Check for open bugs / issues
        if ISSUE_PROMPT=$(python3 "$REPO_DIR/tools/issues.py" --prompt 2>/dev/null) && [ -n "$ISSUE_PROMPT" ]; then
            CYCLE_PROMPT="$ISSUE_PROMPT"
            ISSUE_SUMMARY=$(python3 "$REPO_DIR/tools/issues.py" --summary 2>/dev/null || true)
            SPRINT_BANNER="BUG REPORT PRIORITY ($ISSUE_SUMMARY)"
        elif is_summary_run "$NEXT_RUN" || is_summary_run "$ITERATION"; then
            CYCLE_PROMPT="$SUMMARY_PROMPT"
            SPRINT_BANNER="DOUBLE MILESTONE (Senior PM Meta-Improvement & 10th-Iteration Executive Briefing)"
        elif is_cleanup_run "$NEXT_RUN" || is_cleanup_run "$ITERATION"; then
            CYCLE_PROMPT="$CLEANUP_PROMPT"
            SPRINT_BANNER="CLEANUP SPRINT (Senior Product Manager Meta-Improvement & System Health)"
        fi

        echo ""
        echo "======================================================================"
        echo " Ralph Loop Iteration #$ITERATION (Run #$NEXT_RUN) — $(date '+%Y-%m-%d %H:%M:%S')"
        echo " Cadence:        $SPRINT_BANNER"
        echo "======================================================================"

        set +e
        "$JETSKI_CLI" --dangerously-skip-permissions -p "$CYCLE_PROMPT" --print-timeout "$DEFAULT_TIMEOUT" --output-format stream-json "$@" | python3 "$REPO_DIR/tools/stream_runner.py"
        PIPE_STATUSES=("${PIPESTATUS[@]}")
        EXIT_CODE="${PIPE_STATUSES[0]:-0}"
        FORMATTER_CODE="${PIPE_STATUSES[1]:-0}"
        if [ "$EXIT_CODE" -eq 0 ] && [ "$FORMATTER_CODE" -ne 0 ]; then
            EXIT_CODE="$FORMATTER_CODE"
        fi
        set -e

        if [ "$EXIT_CODE" -ne 0 ]; then
            echo ""
            echo " [!] Iteration #$ITERATION exited with code $EXIT_CODE."
            if [ "$EXIT_CODE" -eq 130 ] || [ "$EXIT_CODE" -eq 2 ]; then
                echo " Interrupted by user. Exiting loop."
                exit 0
            fi
            echo " Pausing 10s before retry..."
            sleep 10
        else
            echo ""
            echo " [✓] Iteration #$ITERATION finished successfully."
            if [ -f "$REPO_DIR/tools/doctor.py" ]; then
                echo " Running repository health check..."
                if ! python3 "$REPO_DIR/tools/doctor.py"; then
                    echo " [!] Doctor health check detected warnings/issues after iteration #$ITERATION!"
                fi
            fi
            echo " Cooldown: Waiting 5s before starting iteration #$((ITERATION + 1))..."
            sleep 5
        fi

        ITERATION=$((ITERATION + 1))
    done
    exit 0
fi

# Explicit Summary Mode (--summary / -s)
if [ "${1:-}" = "--summary" ] || [ "${1:-}" = "-s" ]; then
    shift
    NEXT_RUN=$(get_next_run_number)
    echo "======================================================================"
    echo " Invoking Executive Summary & Trajectory Briefing (Run #$NEXT_RUN)"
    echo "======================================================================"
    if [ "${1:-}" = "--print" ] || [ "${1:-}" = "-p" ]; then
        shift
        set +e
        "$JETSKI_CLI" --dangerously-skip-permissions -p "$SUMMARY_PROMPT" --print-timeout "$DEFAULT_TIMEOUT" --output-format stream-json "$@" | python3 "$REPO_DIR/tools/stream_runner.py"
        EXIT_CODE=$?
        set -e
        exit "$EXIT_CODE"
    fi
    exec "$JETSKI_CLI" --dangerously-skip-permissions -i "$SUMMARY_PROMPT" "$@"
fi

# Explicit Cleanup Mode (--cleanup / -c)
if [ "${1:-}" = "--cleanup" ] || [ "${1:-}" = "-c" ]; then
    shift
    NEXT_RUN=$(get_next_run_number)
    echo "======================================================================"
    echo " Invoking Senior Product Manager Meta-Improvement Sprint (Run #$NEXT_RUN)"
    echo "======================================================================"
    if [ "${1:-}" = "--print" ] || [ "${1:-}" = "-p" ]; then
        shift
        set +e
        "$JETSKI_CLI" --dangerously-skip-permissions -p "$CLEANUP_PROMPT" --print-timeout "$DEFAULT_TIMEOUT" --output-format stream-json "$@" | python3 "$REPO_DIR/tools/stream_runner.py"
        EXIT_CODE=$?
        set -e
        exit "$EXIT_CODE"
    fi
    exec "$JETSKI_CLI" --dangerously-skip-permissions -i "$CLEANUP_PROMPT" "$@"
fi

# Print / Headless Mode (--print / -p)
if [ "${1:-}" = "--print" ] || [ "${1:-}" = "-p" ]; then
    shift
    NEXT_RUN=$(get_next_run_number)
    PROMPT="$DEFAULT_PROMPT"
    if [ "$#" -gt 0 ]; then
        PROMPT="$1"
        shift
    elif ISSUE_PROMPT=$(python3 "$REPO_DIR/tools/issues.py" --prompt 2>/dev/null) && [ -n "$ISSUE_PROMPT" ]; then
        PROMPT="$ISSUE_PROMPT"
    elif is_summary_run "$NEXT_RUN"; then
        PROMPT="$SUMMARY_PROMPT"
    elif is_cleanup_run "$NEXT_RUN"; then
        PROMPT="$CLEANUP_PROMPT"
    fi

    set +e
    "$JETSKI_CLI" --dangerously-skip-permissions -p "$PROMPT" --print-timeout "$DEFAULT_TIMEOUT" --output-format stream-json "$@" | python3 "$REPO_DIR/tools/stream_runner.py"
    EXIT_CODE=$?
    set -e
    exit "$EXIT_CODE"
fi

# Default: Interactive Mode
NEXT_RUN=$(get_next_run_number)
PROMPT="$DEFAULT_PROMPT"
if ISSUE_PROMPT=$(python3 "$REPO_DIR/tools/issues.py" --prompt 2>/dev/null) && [ -n "$ISSUE_PROMPT" ]; then
    PROMPT="$ISSUE_PROMPT"
elif is_summary_run "$NEXT_RUN"; then
    PROMPT="$SUMMARY_PROMPT"
elif is_cleanup_run "$NEXT_RUN"; then
    PROMPT="$CLEANUP_PROMPT"
fi

exec "$JETSKI_CLI" --dangerously-skip-permissions -i "$PROMPT" "$@"

fi # End source guard
