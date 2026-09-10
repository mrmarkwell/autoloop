#!/usr/bin/env python3
"""Autoloop Project Bootstrapper & Seeder.

Bootstraps any directory (Google3 Piper/CitC, Git, or Local) with the complete
autonomous Ralph loop harness, living state machine governance, and developer tooling.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional

AUTOLOOP_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = AUTOLOOP_ROOT / "template"

if str(AUTOLOOP_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOLOOP_ROOT))

from tools.detector import detect_environment
from tools.onboard import ProjectSpec, parse_design_doc, run_interactive_interview


def generate_manifesto(spec: ProjectSpec) -> str:
    pillars_md = "\n".join(f"### {p.split(':')[0]}\n{p}" for p in spec.pillars)
    invariants_md = "\n".join(f"- {inv}" for inv in spec.invariants)

    return f"""# {spec.name} — Project Manifesto

> "{spec.pitch}"

---

## 1. Vision & Core Purpose
{spec.vision}

---

## 2. Core Pillars
{pillars_md}

---

## 3. Non-Negotiable Invariants & Guardrails
{invariants_md}

---

## 4. Autonomous Development Protocol
This codebase is developed, maintained, and self-improved primarily by autonomous LLM agents running in bounded execution loops ("Ralph loops"):
- Every agent is ephemeral, stateless, and self-contained.
- Institutional memory is externalized into living markdown documents (`ROADMAP.md`, `DECISIONS.md`, `AGENT_LOG.md`, `IDEAS.md`).
- Every cycle is tested, verified, and committed cleanly.
"""


def generate_roadmap(spec: ProjectSpec) -> str:
    env = spec.env_profile
    first_tasks = env.suggested_first_tasks if env and env.suggested_first_tasks else [
        "Establish core project architecture and directory skeleton",
        "Implement first unit test verifying build/test pass",
    ]

    phase0_tasks = [
        "- [x] **Task 0.1**: Initialize autonomous harness, living state machines, and developer tooling (ADR-001, ADR-002, ADR-003).",
    ]
    for idx, t in enumerate(first_tasks, start=2):
        phase0_tasks.append(f"- [ ] **Task 0.{idx}**: {t}.")

    phase1_tasks = []
    for idx, t in enumerate(spec.initial_tasks, start=1):
        phase1_tasks.append(f"- [ ] **Task 1.{idx}**: {t}.")

    p0_str = "\n".join(phase0_tasks)
    p1_str = "\n".join(phase1_tasks)

    return f"""# Project Roadmap & Backlog

This document is the single source of truth for current project status, active tasks, and future backlog.
Autonomous agents must consult this document during boot and update it upon completing work.

---

## Current Status Overview
- **Active Phase**: Phase 0 (Harness Setup) & Phase 1 (Domain MVP)
- **Overall Progress**: 1 Completed / {len(phase0_tasks) + len(phase1_tasks)} Total Tasks Tracked
- **Target Environment**: {spec.vcs_type.upper()} ({env.build_system.upper() if env else 'AUTO'})

---

## Phase Breakdown

### Phase 0: Repository Architecture & Autonomous Harness
{p0_str}

### Phase 1: Core Domain MVP & Initial Capabilities
{p1_str}

### Phase 2: System Expansion & Production Hardening
- [ ] **Task 2.1**: High-coverage integration and end-to-end regression test suite.
- [ ] **Task 2.2**: End-user documentation, CLI/API ergonomics, and diagnostic tooling.
"""


def bootstrap_project(target_dir: Path, spec: ProjectSpec) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Bootstrapping project '{spec.name}' into: {target_dir}")

    # 1. Copy template files
    files_to_copy = [
        ".gitignore",
        "ralph.sh",
        "AGENTS.md",
        "GEMINI.md",
        "DECISIONS.md",
        "IDEAS.md",
        "AGENT_LOG.md",
        "BUGS.md",
        "BLOCKED.md.example",
    ]
    for fname in files_to_copy:
        src = TEMPLATE_DIR / fname
        dst = target_dir / fname
        if not dst.exists():
            shutil.copy2(src, dst)
            if fname.endswith(".sh"):
                dst.chmod(0o755)

    # 2. Copy tools directory
    dst_tools = target_dir / "tools"
    dst_tools.mkdir(parents=True, exist_ok=True)
    src_tools = TEMPLATE_DIR / "tools"
    for py_file in src_tools.glob("*.py"):
        dst_py = dst_tools / py_file.name
        shutil.copy2(py_file, dst_py)
        dst_py.chmod(0o755)

    # 3. Generate MANIFESTO.md & ROADMAP.md
    manifesto_path = target_dir / "MANIFESTO.md"
    if not manifesto_path.exists():
        manifesto_path.write_text(generate_manifesto(spec), encoding="utf-8")

    roadmap_path = target_dir / "ROADMAP.md"
    if not roadmap_path.exists():
        roadmap_path.write_text(generate_roadmap(spec), encoding="utf-8")

    # 4. Write config/autoloop.json
    config_dir = target_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "autoloop.json"
    config_file.write_text(json.dumps(spec.to_config_dict(), indent=2), encoding="utf-8")

    # 5. Try installing git hooks if git repository
    if spec.vcs_type == "git":
        import subprocess
        subprocess.run(["python3", "tools/doctor.py", "--install-hooks"], cwd=str(target_dir), check=False)

    print("\n[✓] Project scaffolding successfully deployed!")
    print("----------------------------------------------------------------------")
    print(f" Project Directory: {target_dir}")
    print(f" Environment:       {spec.vcs_type.upper()}")
    print(f" Build Ecosystem:   {spec.env_profile.build_system.upper() if spec.env_profile else 'AUTO'}")
    print("----------------------------------------------------------------------")
    print("To start autonomous development:")
    print(f"  cd {target_dir}")
    print("  ./ralph.sh          # Launch single interactive cycle")
    print("  ./ralph.sh -p       # Launch single headless cycle")
    print("  ./ralph.sh --loop 5 # Launch 5 continuous autonomous cycles")
    print("======================================================================\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Autoloop Autonomous Project Bootstrapper")
    parser.add_argument("target", nargs="?", default=".", help="Target project directory")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive interview wizard")
    parser.add_argument("--from-doc", help="Path to existing markdown PRD / design doc to ingest")
    parser.add_argument("--name", help="Non-interactive: Project name")
    parser.add_argument("--pitch", help="Non-interactive: Project pitch")
    parser.add_argument("--vcs", choices=["piper", "git", "local"], help="Non-interactive: VCS type override")

    args = parser.parse_args(argv)
    target = Path(args.target).resolve()

    # Determine ingestion mode
    if args.from_doc:
        spec = parse_design_doc(Path(args.from_doc).resolve(), target)
    elif args.name:
        env = detect_environment(target)
        spec = ProjectSpec(
            name=args.name,
            pitch=args.pitch or f"{args.name} platform",
            vision=f"High-performance {args.name} platform",
            pillars=["Autonomous development", "Hermetic verification", "High ergonomics"],
            invariants=["100% test pass required", "Hermetic execution"],
            initial_tasks=["Establish initial architecture", "Implement domain logic", "Write unit tests"],
            vcs_type=args.vcs or env.vcs_type,
            env_profile=env,
        )
    else:
        # Default: Interactive interview
        spec = run_interactive_interview(target)

    bootstrap_project(target, spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
