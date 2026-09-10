#!/usr/bin/env python3
"""Executive Summary & Trajectory Briefing Generator for Autoloop.

Analyzes past iterations from AGENT_LOG.md and roadmap progress from ROADMAP.md:
- Computes run velocity (tasks completed per iteration).
- Calculates roadmap completion percentage and estimated remaining iterations.
- Curates multi-run accomplishments and highlights.
- Outputs human executive briefing for human stakeholders.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class RunEntry:
    run_number: int
    title: str
    date_str: str
    actions: List[str] = field(default_factory=list)


@dataclass
class RoadmapStats:
    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    todo_tasks: int = 0
    phases: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    @property
    def completion_pct(self) -> float:
        return (self.completed_tasks / self.total_tasks * 100.0) if self.total_tasks > 0 else 0.0


def parse_agent_log(log_path: Path, window: int = 10) -> List[RunEntry]:
    if not log_path.exists():
        return []

    content = log_path.read_text(encoding="utf-8")
    run_blocks = re.split(r"^##\s+\[Run\s+(\d+)\]", content, flags=re.MULTILINE)
    if len(run_blocks) < 2:
        return []

    runs: List[RunEntry] = []
    # run_blocks[0] is header before first run
    for i in range(1, len(run_blocks), 2):
        run_num = int(run_blocks[i])
        block = run_blocks[i+1]
        first_line = block.strip().split("\n")[0]
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", first_line)
        date_str = date_match.group(1) if date_match else "unknown"

        # Extract actions
        actions = []
        for line in block.split("\n"):
            line_str = line.strip()
            if line_str.startswith("- ") or line_str.startswith("* "):
                clean = line_str.lstrip("-* ").strip()
                if not clean.startswith("**Agent**") and not clean.startswith("**Phase**"):
                    actions.append(clean)

        runs.append(RunEntry(run_number=run_num, title=first_line, date_str=date_str, actions=actions))

    runs.sort(key=lambda r: r.run_number)
    return runs[-window:] if window > 0 else runs


def parse_roadmap(roadmap_path: Path) -> RoadmapStats:
    if not roadmap_path.exists():
        return RoadmapStats()

    content = roadmap_path.read_text(encoding="utf-8")
    task_matches = re.findall(
        r"^-\s+\[( |x|X|TODO|IN PROGRESS|DONE)\]\s+\*\*Task\s+([0-9\.]+)\*\*",
        content,
        re.MULTILINE,
    )

    total = len(task_matches)
    completed = sum(1 for status, _ in task_matches if status in ("x", "X", "DONE"))
    in_progress = sum(1 for status, _ in task_matches if status == "IN PROGRESS")
    todo = sum(1 for status, _ in task_matches if status in (" ", "TODO"))

    # Parse phase headers
    phases: Dict[str, Tuple[int, int]] = {}
    phase_blocks = re.split(r"^###\s+Phase\s+(\d+:[^\n]+)", content, flags=re.MULTILINE)
    for i in range(1, len(phase_blocks), 2):
        pname = phase_blocks[i].strip()
        pcontent = phase_blocks[i+1]
        ptasks = re.findall(r"^-\s+\[( |x|X|TODO|IN PROGRESS|DONE)\]", pcontent, re.MULTILINE)
        pdone = sum(1 for st in ptasks if st in ("x", "X", "DONE"))
        phases[pname] = (pdone, len(ptasks))

    return RoadmapStats(
        total_tasks=total,
        completed_tasks=completed,
        in_progress_tasks=in_progress,
        todo_tasks=todo,
        phases=phases,
    )


def generate_summary(repo_root: Path, window: int = 10) -> str:
    runs = parse_agent_log(repo_root / "AGENT_LOG.md", window=window)
    stats = parse_roadmap(repo_root / "ROADMAP.md")

    lines = []
    lines.append("======================================================================")
    lines.append("                📊 AUTOLOOP EXECUTIVE BRIEFING                        ")
    lines.append("======================================================================")
    lines.append("")

    # 1. Trajectory Overview
    lines.append(f"• Roadmap Completion: {stats.completion_pct:.1f}% ({stats.completed_tasks}/{stats.total_tasks} tasks completed)")
    lines.append(f"• Active Tasks:       {stats.in_progress_tasks} in progress, {stats.todo_tasks} remaining")
    lines.append("")

    # 2. Velocity
    if runs:
        start_run = runs[0].run_number
        end_run = runs[-1].run_number
        run_count = len(runs)
        lines.append(f"• Retrospective Window: Runs #{start_run} – #{end_run} ({run_count} runs analyzed)")
        tasks_per_run = (stats.completed_tasks / max(1, end_run))
        remaining_runs = math.ceil(stats.todo_tasks / max(0.1, tasks_per_run)) if stats.todo_tasks > 0 else 0
        lines.append(f"• Historical Velocity:  ~{tasks_per_run:.2f} tasks/run")
        lines.append(f"• Projected Completion: ~{remaining_runs} autonomous runs remaining")
    lines.append("")

    # 3. Phase Breakdown
    if stats.phases:
        lines.append("----------------------------------------------------------------------")
        lines.append("Phase Breakdown:")
        for pname, (done, total) in stats.phases.items():
            pct = (done / total * 100.0) if total > 0 else 0.0
            lines.append(f"  - Phase {pname}: {pct:.1f}% ({done}/{total})")
        lines.append("")

    # 4. Recent Accomplishments
    if runs:
        lines.append("----------------------------------------------------------------------")
        lines.append(f"Highlights across last {len(runs)} runs:")
        for r in runs[-5:]:
            lines.append(f"  [Run {r.run_number:03d}] {r.title}")
            for act in r.actions[:2]:
                lines.append(f"    • {act[:90]}")
        lines.append("")

    lines.append("======================================================================")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Autoloop Executive Summary Generator")
    parser.add_argument("--window", type=int, default=10, help="Number of past iterations to analyze")
    args = parser.parse_args()

    summary = generate_summary(Path.cwd(), window=args.window)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
