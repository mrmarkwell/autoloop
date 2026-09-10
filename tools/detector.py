#!/usr/bin/env python3
"""Environment and Build System Auto-Detection Engine for Autoloop.

Inspects the target project workspace to infer:
- Version Control System: Piper / CitC, Git, or Local standalone directory.
- Workspace Context: Google3 depot path, CitC client, Git remote.
- Build & Test Ecosystem: Blaze/Bazel, Python (pytest/unittest), Rust (cargo),
  Go, Node/TypeScript, or Unbootstrapped (empty/new project).
- Appropriate formatters, linters, and initial milestone tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EnvironmentProfile:
    """Detected environment, VCS, and build capabilities of a project directory."""
    root_path: Path
    vcs_type: str                         # 'piper', 'git', or 'local'
    vcs_details: Dict[str, Any] = field(default_factory=dict)
    build_system: str = "unbootstrapped"  # 'blaze', 'bazel', 'python', 'cargo', 'go', 'node', 'unbootstrapped'
    test_command: Optional[str] = None
    build_command: Optional[str] = None
    lint_command: Optional[str] = None
    is_empty: bool = False
    suggested_first_tasks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": str(self.root_path),
            "vcs_type": self.vcs_type,
            "vcs_details": self.vcs_details,
            "build_system": self.build_system,
            "test_command": self.test_command,
            "build_command": self.build_command,
            "lint_command": self.lint_command,
            "is_empty": self.is_empty,
            "suggested_first_tasks": self.suggested_first_tasks,
        }


def detect_vcs(path: Path) -> Tuple[str, Dict[str, Any]]:
    """Detect whether a directory belongs to Piper/CitC, Git, or is local."""
    path_str = str(path.resolve())

    # 1. Piper / CitC detection
    # Common CitC patterns: /google/src/cloud/<user>/<workspace>/google3/...
    # Or path contains /google3/
    if "/google/src/cloud/" in path_str or "/google3/" in path_str or path_str.endswith("/google3"):
        details: Dict[str, Any] = {"citc": False}
        m = re.search(r"/google/src/cloud/([^/]+)/([^/]+)", path_str)
        if m:
            details["citc"] = True
            details["user"] = m.group(1)
            details["workspace"] = m.group(2)

        # Extract depot path if applicable
        g3_idx = path_str.find("/google3")
        if g3_idx != -1:
            details["depot_path"] = "//depot" + path_str[g3_idx:]
            details["package_path"] = path_str[g3_idx + len("/google3/"):] if "/google3/" in path_str else path_str[g3_idx + 1:]

        return "piper", details

    # 2. Git detection
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip() == "true":
            details: Dict[str, Any] = {}
            remote_res = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=str(path),
                capture_output=True,
                text=True,
                check=False,
            )
            remote = remote_res.stdout.strip()
            if remote:
                details["remote_url"] = remote
                m = re.search(r"github\.com[:/]([^/]+)/([^/\.]+?)(?:\.git)?$", remote)
                if m:
                    details["owner"] = m.group(1)
                    details["repo"] = m.group(2)
            return "git", details
    except Exception:
        pass

    # 3. Local standalone directory
    return "local", {}


def detect_build_system(path: Path, vcs_type: str, vcs_details: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Detect the build and test ecosystem present in the directory."""
    try:
        entries = [p for p in path.iterdir() if p.name not in (".git", ".hg")]
        if not entries:
            return "unbootstrapped", None, None, None
    except Exception:
        return "unbootstrapped", None, None, None

    # Piper / Google3 environment
    if vcs_type == "piper":
        pkg = vcs_details.get("package_path", "")
        has_build = any(path.glob("**/BUILD")) or any(path.glob("**/BUILD.bazel")) or (path / "BUILD").exists()
        if has_build:
            target = f"//{pkg}/..." if pkg else "//..."
            return "blaze", f"blaze build {target}", f"blaze test {target}", "hg fix"
        return "unbootstrapped", None, None, "hg fix"

    # Bazel in Git/standalone
    if (path / "WORKSPACE").exists() or (path / "WORKSPACE.bazel").exists() or (path / "MODULE.bazel").exists():
        return "bazel", "bazel build //...", "bazel test //...", None

    # Rust Cargo
    if (path / "Cargo.toml").exists():
        return "cargo", "cargo build", "cargo test", "cargo fmt --check"

    # Go Modules
    if (path / "go.mod").exists():
        return "go", "go build ./...", "go test ./...", "gofmt -l ."

    # Python
    py_indicators = [
        path / "pyproject.toml",
        path / "setup.py",
        path / "pytest.ini",
        path / "tox.ini",
        path / "requirements.txt",
    ]
    if any(p.exists() for p in py_indicators) or any(path.glob("**/*.py")):
        has_pytest = (path / "pytest.ini").exists() or (path / "pyproject.toml").exists()
        test_cmd = "pytest" if has_pytest else "python3 -m unittest discover tests"
        return "python", None, test_cmd, None

    # Node / TypeScript
    if (path / "package.json").exists():
        test_cmd = "npm test"
        if (path / "pnpm-lock.yaml").exists():
            test_cmd = "pnpm test"
        elif (path / "yarn.lock").exists():
            test_cmd = "yarn test"
        return "node", "npm run build", test_cmd, "npm run lint"

    return "unbootstrapped", None, None, None


def detect_environment(target_dir: Path) -> EnvironmentProfile:
    """Perform comprehensive auto-detection of a target directory."""
    target_dir = target_dir.resolve()
    vcs_type, vcs_details = detect_vcs(target_dir)
    build_sys, build_cmd, test_cmd, lint_cmd = detect_build_system(target_dir, vcs_type, vcs_details)

    is_empty = True
    if target_dir.exists():
        items = [p for p in target_dir.iterdir() if p.name not in (".git", ".hg")]
        is_empty = len(items) == 0

    first_tasks: List[str] = []
    if is_empty or build_sys == "unbootstrapped":
        if vcs_type == "piper":
            pkg = vcs_details.get("package_path", "your_pkg")
            first_tasks = [
                f"Establish initial BUILD file skeleton under //{pkg} with unit test target",
                "Implement first smoke test verifying blaze test pass",
                "Configure automated doctor verification command in config/autoloop.json",
            ]
        else:
            first_tasks = [
                "Establish core project architecture and directory layout",
                "Implement initial test harness and verifying smoke test",
                "Configure automated doctor verification command in config/autoloop.json",
            ]

    return EnvironmentProfile(
        root_path=target_dir,
        vcs_type=vcs_type,
        vcs_details=vcs_details,
        build_system=build_sys,
        test_command=test_cmd,
        build_command=build_cmd,
        lint_command=lint_cmd,
        is_empty=is_empty,
        suggested_first_tasks=first_tasks,
    )


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    profile = detect_environment(target)
    print(json.dumps(profile.to_dict(), indent=2))
