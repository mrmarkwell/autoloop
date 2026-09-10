#!/usr/bin/env python3
"""Sovereign Zero-Dependency Static Analysis & Google3 Code Hygiene Engine."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
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
  """Audits source and documentation files for syntax, whitespace, and formatting."""

  def __init__(self, root_dir: Path):
    self.root_dir = root_dir.resolve()
    self.is_google3 = "/google3" in str(self.root_dir)

  def lint(self) -> Tuple[bool, List[LintIssue]]:
    issues: List[LintIssue] = []

    # 1. Python source auditing
    for py_file in self.root_dir.glob("**/*.py"):
      if ".git" in py_file.parts or "__pycache__" in py_file.parts:
        continue

      rel = str(py_file.relative_to(self.root_dir))
      try:
        content = py_file.read_text(encoding="utf-8")
        # AST syntax parsing
        ast.parse(content, filename=str(py_file))
      except SyntaxError as syn:
        issues.append(
            LintIssue(
                file_path=rel,
                line=syn.lineno or 0,
                code="E001",
                message=f"Syntax error: {syn.msg}",
            )
        )
      except Exception as exc:
        issues.append(
            LintIssue(
                file_path=rel,
                line=0,
                code="E002",
                message=f"Parse error: {exc}",
            )
        )

      for idx, line in enumerate(content.split("\n"), start=1):
        if line.endswith(" ") or line.endswith("\t"):
          issues.append(
              LintIssue(
                  file_path=rel,
                  line=idx,
                  code="W101",
                  message="Trailing whitespace",
              )
          )
        if self.is_google3 and len(line) > 80:
          # Exclude long URLs or raw docstrings
          if not line.strip().startswith(
              "http"
          ) and not line.strip().startswith('"""'):
            issues.append(
                LintIssue(
                    file_path=rel,
                    line=idx,
                    code="W102",
                    message=f"Line exceeds 80 characters ({len(line)} > 80)",
                )
            )

    # 2. Markdown hygiene auditing
    for md_file in self.root_dir.glob("**/*.md"):
      if ".git" in md_file.parts:
        continue

      rel = str(md_file.relative_to(self.root_dir))
      try:
        content = md_file.read_text(encoding="utf-8")
      except Exception:
        continue

      # Check for raw http links on go-links in Google3
      if self.is_google3:
        if re.search(r"\[go/[^\]]+\]\(http[^\)]+\)", content):
          issues.append(
              LintIssue(
                  file_path=rel,
                  line=1,
                  code="W201",
                  message=(
                      "Explicit hyperlink on go-link is disallowed in Google3"
                      " markdown"
                  ),
              )
          )

    return (len(issues) == 0), issues


def main(argv: Optional[List[str]] = None) -> int:
  parser = argparse.ArgumentParser(description="Autoloop Static Linter")
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
