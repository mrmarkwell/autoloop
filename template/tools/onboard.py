#!/usr/bin/env python3
"""Interactive Onboarding Questionnaire & Design Doc Ingestion Engine for Autoloop.

Allows a developer or project owner to seed a new autonomous project with:
1. High-level vision, core pillars, and architectural boundaries (MANIFESTO.md).
2. Non-negotiable invariants, safety rules, and coding standards.
3. Initial milestones and atomic tasks (ROADMAP.md).
4. Environment & VCS awareness (Google3 Piper/CitC, Git, or Local).
5. Issue tracker configuration (Local BUGS.md, Buganizer, or GitHub).
6. Environment-adaptive verification setup (no prior build commands required!).

Supports both:
- Interactive CLI interview mode.
- Non-interactive design doc ingestion mode (--from-doc design_doc.md).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.detector import detect_environment, EnvironmentProfile


@dataclass
class ProjectSpec:
    name: str
    pitch: str
    vision: str
    pillars: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    initial_tasks: List[str] = field(default_factory=list)
    vcs_type: str = "auto"
    issue_provider: str = "local"
    issue_details: Dict[str, Any] = field(default_factory=dict)
    env_profile: Optional[EnvironmentProfile] = None

    def to_config_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.name,
            "pitch": self.pitch,
            "vcs": {
                "type": self.vcs_type,
                "details": self.env_profile.vcs_details if self.env_profile else {},
            },
            "verification": {
                "build_system": self.env_profile.build_system if self.env_profile else "unbootstrapped",
                "build_command": self.env_profile.build_command if self.env_profile else None,
                "test_command": self.env_profile.test_command if self.env_profile else None,
                "lint_command": self.env_profile.lint_command if self.env_profile else None,
            },
            "issues": {
                "provider": self.issue_provider,
                **self.issue_details,
            },
            "invariants": self.invariants,
        }


def prompt_user(question: str, default: str = "") -> str:
    prompt_str = f"{question} [{default}]: " if default else f"{question}: "
    try:
        val = input(prompt_str).strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)


def run_interactive_interview(target_dir: Path) -> ProjectSpec:
    """Conduct a friendly, interactive onboarding interview with the human author."""
    env = detect_environment(target_dir)
    default_name = target_dir.name or "my_project"

    print("")
    print("======================================================================")
    print("        🚀 Autoloop Autonomous Project Onboarding Wizard              ")
    print("======================================================================")
    print("This wizard configures the autonomous scaffolding so an AI agent can ")
    print("develop, test, and self-improve your project with near-zero code oversight.")
    print("======================================================================")
    print("")

    # 1. Project Identity
    name = prompt_user("1. Project Name", default=default_name)
    pitch = prompt_user("2. One-Line Elevator Pitch", default="Autonomous service and platform engine")
    print("")

    # 2. Vision & Goals
    print("3. High-Level Vision & Core Purpose:")
    print("   What primary problem does this project solve? What is its goal?")
    vision = prompt_user("   Vision Statement", default=f"{name} provides a robust, scalable platform solving mission-critical tasks.")
    print("")

    # 3. Environment & VCS
    print(f"4. Detected Environment: {env.vcs_type.upper()}")
    if env.vcs_type == "piper":
        pkg = env.vcs_details.get("package_path", "")
        print(f"   Identified Piper Google3 package: //{pkg}")
    elif env.vcs_type == "git":
        remote = env.vcs_details.get("remote_url", "local git")
        print(f"   Identified Git repository: {remote}")
    else:
        print("   Standalone / Local directory mode.")
    vcs_choice = prompt_user("   Confirm VCS type (piper / git / local)", default=env.vcs_type)
    print("")

    # 4. Build & Test Guidance
    print(f"5. Build & Test System Status: {env.build_system.upper()}")
    if env.build_system == "unbootstrapped":
        print("   ℹ️  No existing build/test system detected. The autonomous agent will")
        print("      establish the initial build skeleton and smoke test as Phase 0 tasks.")
    else:
        print(f"   Detected test command: {env.test_command}")
    print("")

    # 5. Issue Tracking
    print("6. Bug & Issue Sentry:")
    print("   Where should the agent look for bug reports to prioritize?")
    print("   (1) Local BUGS.md file (Recommended: zero external dependencies, works offline)")
    print("   (2) Google Buganizer Component")
    print("   (3) GitHub Issues")
    issue_sel = prompt_user("   Select issue provider [1/2/3]", default="1")
    issue_provider = "local"
    issue_details: Dict[str, Any] = {"local_file": "BUGS.md"}
    if issue_sel == "2":
        issue_provider = "buganizer"
        comp_id = prompt_user("   Buganizer Component ID", default="0000000")
        issue_details = {"component_id": comp_id}
    elif issue_sel == "3":
        issue_provider = "github"
        owner = prompt_user("   GitHub Owner", default=env.vcs_details.get("owner", "user"))
        repo = prompt_user("   GitHub Repo", default=env.vcs_details.get("repo", name))
        issue_details = {"owner": owner, "repo": repo}
    print("")

    # 6. Non-Negotiable Invariants & Guardrails
    print("7. Non-Negotiable Invariants & Engineering Guardrails:")
    print("   Enter critical rules the agent must never violate (press Enter twice when done):")
    print("   (e.g., 'Ensure all mock buffers zero-initialized', 'Hermetic tests <2s', 'Google style')")
    invariants: List[str] = []
    default_invs = [
        "All code changes must have hermetic unit tests with 100% pass rate.",
        "Zero uninitialized memory in production and mock buffers.",
        "Keep test suite execution fast and deterministic.",
    ]
    for i, inv in enumerate(default_invs, 1):
        custom = prompt_user(f"   Invariant #{i}", default=inv)
        if custom:
            invariants.append(custom)
    print("")

    # 7. Initial Goals / What to Build First
    print("8. Initial Phase 1 Deliverables:")
    print("   What are the first 2-4 concrete features/milestones you want built?")
    initial_tasks: List[str] = []
    default_tasks = [
        "Define core data models, interfaces, and architecture contracts",
        "Implement primary functional domain logic and algorithms",
        "Build hermetic unit test suite verifying core contracts",
        "Implement CLI / entrypoint interface for end users",
    ]
    for i, task in enumerate(default_tasks, 1):
        custom = prompt_user(f"   Task #{i}", default=task)
        if custom:
            initial_tasks.append(custom)

    print("")
    print("======================================================================")
    print(" [✓] Onboarding specifications collected successfully!")
    print("======================================================================")

    return ProjectSpec(
        name=name,
        pitch=pitch,
        vision=vision,
        pillars=[
            "Autonomy & Zero-Maintenance: Designed for continuous self-directed development.",
            "Hermetic Verification: Fast, deterministic unit tests guaranteeing correctness.",
            "High Ergonomics: Clean CLI, well-documented APIs, and transparent state.",
        ],
        invariants=invariants,
        initial_tasks=initial_tasks,
        vcs_type=vcs_choice,
        issue_provider=issue_provider,
        issue_details=issue_details,
        env_profile=env,
    )


def parse_design_doc(doc_path: Path, target_dir: Path) -> ProjectSpec:
    """Parse an existing Markdown PRD or design doc into a structured ProjectSpec."""
    text = doc_path.read_text(encoding="utf-8")
    env = detect_environment(target_dir)

    # Extract Title (# Title)
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    name = title_match.group(1).strip() if title_match else target_dir.name

    # Extract first paragraph as pitch/vision
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    pitch = paragraphs[0][:150] if paragraphs else f"{name} Platform"
    vision = paragraphs[0] if paragraphs else pitch

    # Extract bullet points as tasks
    tasks: List[str] = []
    bullet_matches = re.findall(r"^[*-]\s+([^\n]+)", text, re.MULTILINE)
    for b in bullet_matches:
        clean = b.strip()
        if len(clean) > 15 and not clean.startswith("["):
            tasks.append(clean)
    if not tasks:
        tasks = [
            "Establish core architecture and baseline models",
            "Implement primary domain business logic",
            "Write comprehensive hermetic unit tests",
        ]

    return ProjectSpec(
        name=name,
        pitch=pitch,
        vision=vision,
        pillars=[
            "Autonomous self-improving engineering lifecycle",
            "High test hermeticity and verification velocity",
            "Robust architectural traceability via living ADRs",
        ],
        invariants=[
            "100% hermetic unit test pass required for every commit",
            "Follow project language style guidelines",
            "No uninitialized output parameters in mocks",
        ],
        initial_tasks=tasks[:6],
        vcs_type=env.vcs_type,
        issue_provider="local",
        issue_details={"local_file": "BUGS.md"},
        env_profile=env,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autoloop Onboarding Wizard")
    parser.add_argument("target", nargs="?", default=".", help="Target directory")
    parser.add_argument("--from-doc", help="Path to markdown PRD / design doc to ingest")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if args.from_doc:
        spec = parse_design_doc(Path(args.from_doc), target)
    else:
        spec = run_interactive_interview(target)

    print("\nProject Config JSON Preview:")
    print(json.dumps(spec.to_config_dict(), indent=2))
