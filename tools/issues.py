#!/usr/bin/env python3
"""Configurable Issue & Bug Sentry for Autoloop.

Supports three issue backends:
1. 'local': Reads/writes markdown bugs from BUGS.md (ideal for offline, experimental, or standalone projects).
2. 'buganizer': Google Buganizer component / issue triage.
3. 'github': GitHub Issues API for public or personal open-source projects.

Provides autonomous pre-flight checks (--prompt, --summary, --check) for ralph.sh.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class Issue:
    id: str
    title: str
    body: str = ""
    status: str = "open"  # 'open', 'closed'
    source: str = "local" # 'local', 'buganizer', 'github'
    url: str = ""


class LocalMarkdownIssueBackend:
    """Manages issues in a local BUGS.md file."""

    def __init__(self, bugs_file: Path):
        self.bugs_file = bugs_file

    def _ensure_file(self) -> None:
        if not self.bugs_file.exists():
            self.bugs_file.write_text(
                "# Bug Reports & Issue Queue\n\n"
                "This file tracks open issues and bug reports for autonomous triage.\n\n"
                "## Open Issues\n\n"
                "<!-- Format: ### [BUG-101] Title -->\n\n"
                "## Closed Issues\n\n",
                encoding="utf-8",
            )

    def list_open(self) -> List[Issue]:
        if not self.bugs_file.exists():
            return []
        content = self.bugs_file.read_text(encoding="utf-8")
        if "## Open Issues" not in content:
            return []

        open_section = content.split("## Open Issues")[-1]
        if "## Closed Issues" in open_section:
            open_section = open_section.split("## Closed Issues")[0]

        issues: List[Issue] = []
        matches = re.finditer(r"###\s+\[([^\]]+)\]\s+([^\n]+)(.*?)(?=(?:###\s+\[|$))", open_section, re.DOTALL)
        for m in matches:
            bug_id = m.group(1).strip()
            title = m.group(2).strip()
            body = m.group(3).strip()
            issues.append(Issue(id=bug_id, title=title, body=body, status="open", source="local"))

        return issues

    def close(self, issue_id: str, reason: str = "Resolved") -> bool:
        if not self.bugs_file.exists():
            return False
        content = self.bugs_file.read_text(encoding="utf-8")
        pattern = rf"(###\s+\[{re.escape(issue_id)}\]\s+[^\n]+.*?)(?=(?:###\s+\[|## Closed Issues|$))"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return False

        block = match.group(1).strip()
        # Remove from open
        content = content[:match.start(1)] + content[match.end(1):]
        # Append to closed
        closed_marker = "## Closed Issues"
        if closed_marker in content:
            closed_entry = f"\n\n{block}\n- **Resolution**: {reason}\n"
            content = content.replace(closed_marker, closed_marker + closed_entry, 1)

        self.bugs_file.write_text(content, encoding="utf-8")
        return True


class GitHubIssueBackend:
    """Manages issues via GitHub REST API."""

    def __init__(self, owner: str, repo: str, token: Optional[str] = None):
        self.owner = owner
        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def list_open(self) -> List[Issue]:
        from urllib import request as url_request, error as url_error
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues?state=open&per_page=10"
        headers = {
            "User-Agent": "Autoloop-Agent/1.0",
            "Accept": "application/vnd.github+json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = url_request.Request(url, headers=headers)
        try:
            with url_request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                issues = []
                for item in data:
                    if "pull_request" in item:
                        continue
                    issues.append(Issue(
                        id=str(item["number"]),
                        title=item.get("title", ""),
                        body=item.get("body", "") or "",
                        status="open",
                        source="github",
                        url=item.get("html_url", ""),
                    ))
                return issues
        except Exception:
            return []


class IssueManager:
    """Dispatches issue operations to configured backend."""

    def __init__(self, root_dir: Path, config: Optional[Dict[str, Any]] = None):
        self.root_dir = root_dir.resolve()
        self.config = config or {}
        issue_cfg = self.config.get("issues", {})
        self.provider = issue_cfg.get("provider", "local")

        if self.provider == "github":
            owner = issue_cfg.get("owner", "")
            repo = issue_cfg.get("repo", "")
            if not owner or not repo:
                from tools.detector import detect_vcs
                _, vcs_details = detect_vcs(self.root_dir)
                owner = owner or vcs_details.get("owner", "")
                repo = repo or vcs_details.get("repo", "")
            self.backend = GitHubIssueBackend(owner, repo)
        else:
            bugs_file = self.root_dir / issue_cfg.get("local_file", "BUGS.md")
            self.backend = LocalMarkdownIssueBackend(bugs_file)

    def check(self) -> Tuple[bool, List[Issue]]:
        issues = self.backend.list_open()
        return (len(issues) > 0), issues

    def prompt(self) -> str:
        has_issues, issues = self.check()
        if not has_issues:
            return ""
        first = issues[0]
        snippet = first.body[:250].replace("\n", " ") if first.body else "No description provided."
        return (
            f"PRIORITY 1: Open bug report detected [{first.id}]: \"{first.title}\". "
            f"Details: {snippet}. "
            f"Before taking on roadmap tasks, reproduce the issue, write a regression unit test, "
            f"fix the bug, verify all tests pass, and close the issue."
        )

    def summary(self) -> str:
        has_issues, issues = self.check()
        if not has_issues:
            return ""
        return f"Open Issue [{issues[0].id}]: {issues[0].title}"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Autoloop Issue Triage Engine")
    parser.add_argument("action", nargs="?", default="check", choices=["check", "list", "close"])
    parser.add_argument("--prompt", action="store_true", help="Emit autonomous prompt string")
    parser.add_argument("--summary", action="store_true", help="Emit one-line summary")
    parser.add_argument("--quiet", action="store_true", help="Silent exit code only")
    parser.add_argument("--issue-id", help="Issue ID to operate on")
    parser.add_argument("--reason", default="Resolved with regression test", help="Resolution reason")

    args = parser.parse_args(argv)
    mgr = IssueManager(Path.cwd())

    if args.prompt:
        p = mgr.prompt()
        if p:
            print(p)
            return 0
        return 1

    if args.summary:
        s = mgr.summary()
        if s:
            print(s)
            return 0
        return 1

    has_issues, issues = mgr.check()
    if args.quiet:
        return 0 if has_issues else 1

    if has_issues:
        print(f"Found {len(issues)} open issue(s):")
        for iss in issues:
            print(f"  - [{iss.id}] {iss.title}")
        return 0
    else:
        print("0 open issues detected.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
