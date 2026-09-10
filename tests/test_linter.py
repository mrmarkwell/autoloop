"""Hermetic unit tests for ProjectLinter."""

from pathlib import Path
import tempfile
import unittest

from tools.linter import ProjectLinter


class TestLinter(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_file_passes(self):
        (self.root / "clean.py").write_text("def hello():\n    return 'world'\n")
        linter = ProjectLinter(self.root)
        ok, issues = linter.lint()
        self.assertTrue(ok)
        self.assertEqual(len(issues), 0)

    def test_syntax_error_detected(self):
        (self.root / "bad.py").write_text("def bad(\n")
        linter = ProjectLinter(self.root)
        ok, issues = linter.lint()
        self.assertFalse(ok)
        self.assertEqual(issues[0].code, "E001")


if __name__ == "__main__":
    unittest.main()
