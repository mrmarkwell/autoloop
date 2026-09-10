#!/usr/bin/env python3
"""Sovereign Zero-Dependency Static Analysis & Code Hygiene Engine."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import List, Optional, Tuple


@dataclass
class LintIssue:
    file_path: str
    line: int
    code: str
    message: str


class ProjectLinter:
    """Audits Python files for bytecode/AST syntax errors and hygiene."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()

    def lint(self) -> Tuple[bool, List[LintIssue]]:
        issues: List[LintIssue] = []
        for py_file in self.root_dir.glob("**/*.py"):
            if ".git" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            rel = str(py_file.relative_to(self.root_dir))
            try:
                content = py_file.read_text(encoding="utf-8")
                # 1. AST syntax parsing
                ast.parse(content, filename=str(py_file))
            except SyntaxError as syn:
                issues.append(LintIssue(file_path=rel, line=syn.lineno or 0, code="E001", message=f"Syntax error: {syn.msg}"))
            except Exception as exc:
                issues.append(LintIssue(file_path=rel, line=0, code="E002", message=f"Parse error: {exc}"))

            # 2. Line hygiene: trailing whitespace
            for idx, line in enumerate(content.split("\n"), start=1):
                if line.endswith(" ") or line.endswith("\t"):
                    issues.append(LintIssue(file_path=rel, line=idx, code="W101", message="Trailing whitespace"))

        return (len(issues) == 0), issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Keel Static Linter")
    parser.add_argument("root", nargs="?", default=".", help="Root path to lint")
    args = parser.parse_args(argv)

    t0 = time.time()
    linter = ProjectLinter(Path(args.root))
    ok, issues = linter.lint()
    dur = time.time() - t0

    if ok:
        print(f"✔ 100% Clean — 0 static analysis issues found ({dur:.3f}s)")
        return 0
    else:
        print(f"✘ Found {len(issues)} static analysis issue(s) ({dur:.3f}s):")
        for iss in issues:
            print(f"  {iss.file_path}:{iss.line} [{iss.code}] {iss.message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
