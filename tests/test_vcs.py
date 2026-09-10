#!/usr/bin/env python3
"""Hermetic unit tests for Autoloop VCS adapter."""

from pathlib import Path
import tempfile
import unittest

from tools.vcs import VCSAdapter


class TestVCSAdapter(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_local_mode_checkpoint(self):
        vcs = VCSAdapter(self.root, vcs_type="local")
        self.assertEqual(vcs.vcs_type, "local")
        self.assertFalse(vcs.has_changes())

        # Local commit
        res = vcs.commit("feat: test commit")
        self.assertTrue(res.success)
        self.assertIn("Local mode checkpoint", res.stdout)

        # Local push
        push_res = vcs.push()
        self.assertTrue(push_res.success)

    def test_empty_commit_message_fails(self):
        vcs = VCSAdapter(self.root, vcs_type="local")
        res = vcs.commit("   ")
        self.assertFalse(res.success)
        self.assertIn("empty", res.stderr)


if __name__ == "__main__":
    unittest.main()
