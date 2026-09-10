#!/usr/bin/env python3
"""Hermetic unit tests for Autoloop issues triage engine."""

from pathlib import Path
import tempfile
import unittest

from tools.issues import LocalMarkdownIssueBackend, IssueManager


class TestIssues(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.bugs_file = self.root / "BUGS.md"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_local_issue_lifecycle(self):
        backend = LocalMarkdownIssueBackend(self.bugs_file)
        self.assertEqual(backend.list_open(), [])

        # Write an issue
        self.bugs_file.write_text(
            "# Bug Reports\n\n## Open Issues\n\n### [BUG-001] Fix memory allocation\nUninitialized buffer in matrix.\n\n## Closed Issues\n",
            encoding="utf-8"
        )
        issues = backend.list_open()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].id, "BUG-001")
        self.assertEqual(issues[0].title, "Fix memory allocation")

        # Close issue
        ok = backend.close("BUG-001", reason="Fixed with absl::c_fill")
        self.assertTrue(ok)
        self.assertEqual(backend.list_open(), [])
        content = self.bugs_file.read_text(encoding="utf-8")
        self.assertIn("## Closed Issues", content)
        self.assertIn("BUG-001", content)
        self.assertIn("Fixed with absl::c_fill", content)

    def test_issue_manager_prompt(self):
        self.bugs_file.write_text(
            "# Bug Reports\n\n## Open Issues\n\n### [BUG-002] Crash on empty input\nNull pointer crash.\n\n## Closed Issues\n",
            encoding="utf-8"
        )
        mgr = IssueManager(self.root, config={"issues": {"provider": "local", "local_file": "BUGS.md"}})
        has_issues, issues = mgr.check()
        self.assertTrue(has_issues)
        prompt = mgr.prompt()
        self.assertIn("PRIORITY 1", prompt)
        self.assertIn("BUG-002", prompt)


if __name__ == "__main__":
    unittest.main()
