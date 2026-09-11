#!/usr/bin/env python3
"""Unified Version Control System (VCS) Adapter for Autoloop.

Abstracts version control operations across:
- Google3 Piper / CitC (hg / fig / CitC snapshots)
- Git (local worktrees, GitHub, Git-on-Borg)
- Local directory (standalone / offline prototyping)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class VCSResult:
    """Outcome of a VCS command execution."""
    success: bool
    stdout: str
    stderr: str
    returncode: int


class VCSAdapter:
    """Universal interface for VCS interactions."""

    def __init__(self, root_dir: Path, vcs_type: str = "auto", config: Optional[Dict[str, Any]] = None):
        self.root_dir = root_dir.resolve()
        self.config = config or {}
        if vcs_type == "auto":
            from tools.detector import detect_vcs
            self.vcs_type, self.vcs_details = detect_vcs(self.root_dir)
        else:
            self.vcs_type = vcs_type
            self.vcs_details = self.config.get("vcs_details", {})

    def _run(self, cmd: List[str]) -> VCSResult:
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            return VCSResult(
                success=(res.returncode == 0),
                stdout=res.stdout.strip(),
                stderr=res.stderr.strip(),
                returncode=res.returncode,
            )
        except Exception as exc:
            return VCSResult(success=False, stdout="", stderr=str(exc), returncode=1)

    def status(self) -> VCSResult:
        """Query working directory status (modified, untracked, deleted files)."""
        if self.vcs_type == "piper":
            return self._run(["hg", "status", "."])
        elif self.vcs_type == "git":
            return self._run(["git", "status", "--porcelain"])
        else:
            return VCSResult(success=True, stdout="Local mode: all changes untracked", stderr="", returncode=0)

    def has_changes(self) -> bool:
        """Check if there are any uncommitted or modified files."""
        res = self.status()
        if self.vcs_type in ("piper", "git"):
            return bool(res.stdout.strip())
        return False

    def commit(self, message: str) -> VCSResult:
        """Stage and commit changes with the specified message."""
        clean_msg = message.strip()
        if not clean_msg:
            return VCSResult(success=False, stdout="", stderr="Commit message cannot be empty", returncode=1)

        if self.vcs_type == "piper":
            self._run(["hg", "addremove", "."])
            return self._run(["hg", "commit", "-m", clean_msg, "."])
        elif self.vcs_type == "git":
            add_res = self._run(["git", "add", "-A"])
            if not add_res.success:
                return add_res
            return self._run(["git", "commit", "-m", clean_msg])
        else:
            return VCSResult(
                success=True,
                stdout=f"Local mode checkpoint: {clean_msg}",
                stderr="",
                returncode=0,
            )

    def push(self) -> VCSResult:
        """Push or sync committed changes to remote / depot."""
        if self.vcs_type == "piper":
            return VCSResult(
                success=True,
                stdout="CitC workspace synced automatically to cloud depot",
                stderr="",
                returncode=0,
            )
        elif self.vcs_type == "git":
            branch_res = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            branch = branch_res.stdout if branch_res.success and branch_res.stdout else "main"
            return self._run(["git", "push", "origin", branch])
        else:
            return VCSResult(
                success=True,
                stdout="Local mode: no remote to push to",
                stderr="",
                returncode=0,
            )

    def diff(self) -> str:
        """Return diff of current uncommitted changes."""
        if self.vcs_type == "piper":
            res = self._run(["hg", "diff"])
            return res.stdout
        elif self.vcs_type == "git":
            res = self._run(["git", "diff", "HEAD"])
            return res.stdout
        return ""

    def get_branch(self) -> str:
        """Return the current branch or workspace identifier."""
        if self.vcs_type == "git":
            res = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            return res.stdout if res.success and res.stdout else "main"
        elif self.vcs_type == "piper":
            return self.vcs_details.get("citc_client", "CitC")
        return "local"

    def get_tracking_status(self) -> str:
        """Return upstream tracking information."""
        if self.vcs_type == "git":
            res = self._run(["git", "status", "-sb"])
            if res.success and res.stdout:
                line = res.stdout.splitlines()[0]
                if "..." in line:
                    tail = line.split("...")[1]
                    if "[" in tail:
                        return tail[tail.index("[") :]
                    return f"up to date with {tail}"
            return "local only"
        elif self.vcs_type == "piper":
            return "synced with cloud depot"
        return "standalone"

    def get_latest_commit(self) -> str:
        """Return short description of the most recent commit or revision."""
        if self.vcs_type == "git":
            res = self._run(["git", "log", "-1", "--format=%h — %s (%cr)"])
            return res.stdout if res.success and res.stdout else ""
        elif self.vcs_type == "piper":
            res = self._run(["hg", "log", "-r", ".", "--template", "{node|short} — {desc|firstline}"])
            return res.stdout if res.success and res.stdout else ""
        return ""

    def get_detailed_status(self) -> Dict[str, Any]:
        """Return comprehensive working tree breakdown for executive status."""
        st = self.status()
        clean = True
        staged_cnt = 0
        mod_cnt = 0
        untracked_cnt = 0
        changed: List[str] = []

        if st.stdout.strip():
            lines = [l for l in st.stdout.splitlines() if l.strip()]
            if lines and lines[0] != "Local mode: all changes untracked":
                clean = False
                for l in lines:
                    prefix = l[:2]
                    changed.append(l)
                    if prefix == "??":
                        untracked_cnt += 1
                    else:
                        if prefix[0] in "MADRC":
                            staged_cnt += 1
                        if len(prefix) > 1 and prefix[1] in "MD":
                            mod_cnt += 1

        return {
            "vcs_type": self.vcs_type,
            "branch": self.get_branch(),
            "tracking": self.get_tracking_status(),
            "clean": clean,
            "staged_count": staged_cnt,
            "modified_count": mod_cnt,
            "untracked_count": untracked_cnt,
            "changed_files": changed,
            "latest_commit": self.get_latest_commit(),
        }


if __name__ == "__main__":
    target = Path.cwd()
    vcs = VCSAdapter(target)
    print(f"VCS Type: {vcs.vcs_type}")
    print(f"Has Changes: {vcs.has_changes()}")
    st = vcs.status()
    if st.stdout:
        print("Status:\n" + st.stdout)
