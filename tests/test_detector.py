#!/usr/bin/env python3
"""Hermetic unit tests for Autoloop environment detector."""

import os
from pathlib import Path
import tempfile
import unittest

from tools.detector import detect_build_system, detect_environment, detect_vcs


class TestDetector(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_detect_local_empty_dir(self):
        profile = detect_environment(self.root)
        self.assertEqual(profile.vcs_type, "local")
        self.assertEqual(profile.build_system, "unbootstrapped")
        self.assertTrue(profile.is_empty)
        self.assertGreater(len(profile.suggested_first_tasks), 0)

    def test_detect_cargo(self):
        (self.root / "Cargo.toml").write_text("[package]\nname = \"foo\"\n")
        build_sys, build_cmd, test_cmd, _ = detect_build_system(self.root, "local", {})
        self.assertEqual(build_sys, "cargo")
        self.assertEqual(test_cmd, "cargo test")

    def test_detect_python(self):
        (self.root / "pyproject.toml").write_text("[build-system]\nrequires = []\n")
        build_sys, _, test_cmd, _ = detect_build_system(self.root, "local", {})
        self.assertEqual(build_sys, "python")
        self.assertEqual(test_cmd, "pytest")

    def test_detect_go(self):
        (self.root / "go.mod").write_text("module example.com/foo\n")
        build_sys, _, test_cmd, _ = detect_build_system(self.root, "local", {})
        self.assertEqual(build_sys, "go")
        self.assertEqual(test_cmd, "go test ./...")

    def test_detect_piper_citc(self):
        fake_citc = Path("/google/src/cloud/testuser/myws/google3/experimental/users/testuser/foo")
        vcs_type, details = detect_vcs(fake_citc)
        self.assertEqual(vcs_type, "piper")
        self.assertTrue(details.get("citc"))
        self.assertEqual(details.get("user"), "testuser")
        self.assertEqual(details.get("workspace"), "myws")
        self.assertEqual(details.get("package_path"), "experimental/users/testuser/foo")


if __name__ == "__main__":
    unittest.main()
