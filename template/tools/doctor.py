#!/usr/bin/env python3
"""Automated Repository Doctor & Health Verification Engine for Autoloop.

Diagnoses project health and enforces invariant integrity:
1. State-Machine Synchronization (ADRs, AGENT_LOG run sequence, ROADMAP tasks).
2. Static AST & Hygiene Linter (tools/linter.py).
3. Build & Test Health (blaze test, pytest, etc.).
4. VCS & Merge Conflict Integrity.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from tools.linter import ProjectLinter
from tools.vcs import VCSAdapter
from tools.verifier import ProjectVerifier


@dataclass
class CheckResult:
  name: str
  passed: bool
  details: str
  duration_sec: float = 0.0


class DoctorStyler:

  def __init__(self, enabled: bool = True):
    self.enabled = enabled

  def _wrap(self, code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if self.enabled else text

  def bold(self, text: str) -> str:
    return self._wrap("1", text)

  def green(self, text: str) -> str:
    return self._wrap("32", text)

  def red(self, text: str) -> str:
    return self._wrap("31", text)


def check_doc_synchronization(repo_root: Path) -> CheckResult:
  """Verify state machine synchronization across project governance documents."""
  t0 = time.time()
  issues: List[str] = []

  decisions_file = repo_root / "DECISIONS.md"
  agent_log_file = repo_root / "AGENT_LOG.md"
  roadmap_file = repo_root / "ROADMAP.md"
  ideas_file = repo_root / "IDEAS.md"

  if not decisions_file.exists():
    issues.append("Missing DECISIONS.md")
  if not agent_log_file.exists():
    issues.append("Missing AGENT_LOG.md")
  if not roadmap_file.exists():
    issues.append("Missing ROADMAP.md")
  if not ideas_file.exists():
    issues.append("Missing IDEAS.md")

  if issues:
    return CheckResult(
        "Documentation State Sync", False, "\n  ".join(issues), time.time() - t0
    )

  decisions_text = decisions_file.read_text(encoding="utf-8")
  defined_adrs = set(re.findall(r"ADR-\d+", decisions_text))

  agent_log_text = agent_log_file.read_text(encoding="utf-8")
  referenced_adrs = set(re.findall(r"ADR-\d+", agent_log_text))

  unresolved_adrs = referenced_adrs - defined_adrs
  if unresolved_adrs:
    issues.append(
        f"AGENT_LOG.md references undefined ADRs: {sorted(unresolved_adrs)}"
    )

  runs = [int(x) for x in re.findall(r"\[Run (\d+)\]", agent_log_text)]
  if runs and runs != [0]:
    filtered_runs = [r for r in runs if r > 0]
    if filtered_runs:
      expected = list(range(1, len(filtered_runs) + 1))
      if filtered_runs != expected:
        issues.append(
            f"AGENT_LOG.md run numbers are non-contiguous: {filtered_runs}"
        )

  roadmap_text = roadmap_file.read_text(encoding="utf-8")
  task_matches = re.findall(
      r"^-\s+\[( |x|X|TODO|IN PROGRESS|DONE)\]\s+\*\*Task\s+([0-9\.]+)\*\*",
      roadmap_text,
      re.MULTILINE,
  )
  if task_matches:
    task_ids = [t[1] for t in task_matches]
    seen = set()
    duplicates = set()
    for tid in task_ids:
      if tid in seen:
        duplicates.add(tid)
      seen.add(tid)
    if duplicates:
      issues.append(
          f"ROADMAP.md contains duplicate task IDs: {sorted(duplicates)}"
      )

  dur = time.time() - t0
  if issues:
    return CheckResult(
        "Documentation State Sync", False, "\n  ".join(issues), dur
    )

  return CheckResult(
      "Documentation State Sync",
      True,
      f"{len(defined_adrs)} ADRs registered, {len(runs)} run entries logged,"
      f" {len(task_matches)} roadmap tasks tracked",
      dur,
  )


def check_merge_conflicts(repo_root: Path) -> CheckResult:
  """Verify there are no git/VCS conflict markers in tracked text files."""
  t0 = time.time()
  conflict_pattern = re.compile(r"^(<{7}|={7}|>{7})\s+", re.MULTILINE)
  offenders: List[str] = []

  for ext in (
      "*.py",
      "*.md",
      "*.json",
      "*.sh",
      "*.rs",
      "*.go",
      "*.ts",
      "*.java",
      "*.cc",
      "*.h",
      "BUILD",
  ):
    for path in repo_root.glob(f"**/{ext}"):
      if ".git" in path.parts:
        continue
      try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if conflict_pattern.search(content):
          offenders.append(str(path.relative_to(repo_root)))
      except Exception:
        pass

  dur = time.time() - t0
  if offenders:
    return CheckResult(
        "Conflict Markers Check",
        False,
        f"Found merge conflict markers in: {offenders}",
        dur,
    )
  return CheckResult(
      "Conflict Markers Check", True, "Zero merge conflict markers found", dur
  )


def check_static_hygiene(repo_root: Path) -> CheckResult:
  """Verify Python AST syntax and formatting hygiene via tools/linter.py."""
  t0 = time.time()
  linter = ProjectLinter(repo_root)
  ok, issues = linter.lint()
  dur = time.time() - t0
  if not ok:
    details = "\n  ".join(
        f"{iss.file_path}:{iss.line} [{iss.code}] {iss.message}"
        for iss in issues[:5]
    )
    if len(issues) > 5:
      details += f"\n  ... and {len(issues) - 5} more issues"
    return CheckResult("Static Code Hygiene", False, details, dur)
  return CheckResult(
      "Static Code Hygiene", True, "0 static analysis findings", dur
  )


def check_build_and_tests(repo_root: Path) -> CheckResult:
  """Verify the project's build and test suite passes."""
  t0 = time.time()
  verifier = ProjectVerifier(repo_root)
  ok, results = verifier.verify_all()
  dur = time.time() - t0

  failed = [r for r in results if not r.passed and not r.skipped]
  if failed:
    details = "\n  ".join(
        f"{r.name}: {r.message} (stderr: {r.stderr[:200]})" for r in failed
    )
    return CheckResult("Build & Test Verification", False, details, dur)

  summary_parts = []
  for r in results:
    if r.skipped:
      summary_parts.append(f"{r.name} skipped")
    else:
      summary_parts.append(f"{r.name} passed ({r.duration_sec:.2f}s)")

  return CheckResult(
      "Build & Test Verification",
      True,
      ", ".join(summary_parts) if summary_parts else "All verifications passed",
      dur,
  )


def run_doctor(
    repo_root: Path, fast: bool = False
) -> Tuple[bool, List[CheckResult]]:
  checks = [
      (
          "Documentation Synchronization",
          lambda: check_doc_synchronization(repo_root),
      ),
      ("Workspace Conflict Markers", lambda: check_merge_conflicts(repo_root)),
      ("Static Code Hygiene", lambda: check_static_hygiene(repo_root)),
  ]
  if not fast:
    checks.append(
        ("Build & Test Verification", lambda: check_build_and_tests(repo_root))
    )

  results: List[CheckResult] = []
  all_passed = True
  for name, fn in checks:
    res = fn()
    results.append(res)
    if not res.passed:
      all_passed = False

  return all_passed, results


def main(argv: Optional[List[str]] = None) -> int:
  parser = argparse.ArgumentParser(
      description="Autoloop Repository Health & Invariant Doctor"
  )
  parser.add_argument(
      "--fast",
      action="store_true",
      help="Run fast checks only (<0.2s pre-commit mode)",
  )
  parser.add_argument(
      "--json", action="store_true", help="Output machine-readable JSON"
  )

  args = parser.parse_args(argv)
  repo_root = Path.cwd()

  all_passed, results = run_doctor(repo_root, fast=args.fast)

  if args.json:
    payload = {
        "passed": all_passed,
        "checks": [
            {
                "name": r.name,
                "passed": r.passed,
                "details": r.details,
                "duration_sec": r.duration_sec,
            }
            for r in results
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0 if all_passed else 1

  styler = DoctorStyler()
  print(
      "======================================================================"
  )
  print(
      "                🩺 Autoloop Repository Doctor & Health Audit           "
  )
  print(
      "======================================================================"
  )
  for r in results:
    icon = styler.green("✔ PASS") if r.passed else styler.red("✘ FAIL")
    print(f"[{icon}] {styler.bold(r.name)} ({r.duration_sec:.2f}s)")
    print(f"       {r.details}")
  print(
      "----------------------------------------------------------------------"
  )
  if all_passed:
    print(
        styler.green("Result: 100% HEALTHY — Ready for autonomous development.")
    )
    return 0
  else:
    print(
        styler.red("Result: ISSUES DETECTED — Please resolve findings above.")
    )
    return 1


if __name__ == "__main__":
  sys.exit(main())
