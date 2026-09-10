#!/usr/bin/env python3
"""Configurable Build & Test Verification Engine for Autoloop.

Executes project build, test, and lint commands.
Handles both established projects (running blaze, pytest, cargo, etc.)
and unbootstrapped new projects where tests are established in Phase 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class CommandResult:
    name: str
    command: str
    passed: bool
    duration_sec: float
    stdout: str
    stderr: str
    skipped: bool = False
    message: str = ""


class ProjectVerifier:
    """Runs build, test, and lint checks against the project."""

    def __init__(self, root_dir: Path, config: Optional[Dict[str, Any]] = None):
        self.root_dir = root_dir.resolve()
        self.config = config or {}

        # Load from config/autoloop.json if not provided
        if not self.config:
            cfg_file = self.root_dir / "config" / "autoloop.json"
            if cfg_file.exists():
                try:
                    import json
                    self.config = json.loads(cfg_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

        verif_cfg = self.config.get("verification", {})
        self.build_system = verif_cfg.get("build_system", "")
        self.build_cmd = verif_cfg.get("build_command")
        self.test_cmd = verif_cfg.get("test_command")
        self.lint_cmd = verif_cfg.get("lint_command")
        self.timeout_sec = float(verif_cfg.get("timeout_sec", 120.0))

        if not self.test_cmd:
            from tools.detector import detect_environment
            profile = detect_environment(self.root_dir)
            # If tests directory now exists with test files, auto-upgrade from unbootstrapped
            if profile.test_command:
                self.test_cmd = profile.test_command
                self.build_cmd = self.build_cmd or profile.build_command
                self.lint_cmd = self.lint_cmd or profile.lint_command
                self.build_system = profile.build_system

    def _execute(self, name: str, cmd_str: Optional[str]) -> CommandResult:
        if not cmd_str or not cmd_str.strip():
            return CommandResult(
                name=name,
                command="",
                passed=True,
                duration_sec=0.0,
                stdout="",
                stderr="",
                skipped=True,
                message=f"Pending setup (Phase 0 will establish {name.lower()} command)",
            )

        # Check if running python unittest on a non-existent tests directory
        if "unittest discover" in cmd_str and not (self.root_dir / "tests").exists():
            return CommandResult(
                name=name,
                command=cmd_str,
                passed=True,
                duration_sec=0.0,
                stdout="",
                stderr="",
                skipped=True,
                message="Pending bootstrap (tests directory will be created in Phase 0)",
            )

        t0 = time.time()
        try:
            res = subprocess.run(
                cmd_str,
                shell=True,
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
            dur = time.time() - t0
            passed = (res.returncode == 0)
            msg = f"{name} passed in {dur:.2f}s" if passed else f"{name} failed with exit code {res.returncode}"
            return CommandResult(
                name=name,
                command=cmd_str,
                passed=passed,
                duration_sec=dur,
                stdout=res.stdout.strip(),
                stderr=res.stderr.strip(),
                skipped=False,
                message=msg,
            )
        except subprocess.TimeoutExpired:
            dur = time.time() - t0
            return CommandResult(
                name=name,
                command=cmd_str,
                passed=False,
                duration_sec=dur,
                stdout="",
                stderr=f"Command timed out after {self.timeout_sec}s",
                skipped=False,
                message=f"{name} timed out",
            )
        except Exception as exc:
            dur = time.time() - t0
            return CommandResult(
                name=name,
                command=cmd_str,
                passed=False,
                duration_sec=dur,
                stdout="",
                stderr=str(exc),
                skipped=False,
                message=f"Execution error: {exc}",
            )

    def verify_build(self) -> CommandResult:
        return self._execute("Build", self.build_cmd)

    def verify_tests(self) -> CommandResult:
        return self._execute("Tests", self.test_cmd)

    def verify_lint(self) -> CommandResult:
        return self._execute("Lint", self.lint_cmd)

    def verify_all(self) -> Tuple[bool, List[CommandResult]]:
        results = []
        if self.build_cmd:
            build_res = self.verify_build()
            results.append(build_res)
            if not build_res.passed and not build_res.skipped:
                return False, results

        test_res = self.verify_tests()
        results.append(test_res)

        if self.lint_cmd:
            results.append(self.verify_lint())

        all_passed = all(r.passed for r in results if not r.skipped)
        return all_passed, results


if __name__ == "__main__":
    verifier = ProjectVerifier(Path.cwd())
    ok, results = verifier.verify_all()
    for r in results:
        status = "SKIPPED" if r.skipped else ("PASSED" if r.passed else "FAILED")
        print(f"[{status}] {r.name}: {r.message} ({r.duration_sec:.2f}s)")
    sys.exit(0 if ok else 1)
