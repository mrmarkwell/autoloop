#!/usr/bin/env python3
"""Hermetic unit tests for Autoloop project bootstrapper."""

import json
from pathlib import Path
import tempfile
import unittest

from seed import bootstrap_project
from tools.detector import EnvironmentProfile
from tools.doctor import run_doctor
from tools.onboard import ProjectSpec


class TestSeed(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp_dir.name) / "seeded_proj"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_bootstrap_and_doctor_pass(self):
        spec = ProjectSpec(
            name="SampleApp",
            pitch="High-throughput retrieval service",
            vision="Provide sub-millisecond retrieval",
            pillars=["Speed", "Accuracy"],
            invariants=["100% test pass"],
            initial_tasks=["Build index", "Add query API"],
            vcs_type="local",
            env_profile=EnvironmentProfile(
                root_path=self.target,
                vcs_type="local",
                build_system="unbootstrapped",
                is_empty=True,
            )
        )

        bootstrap_project(self.target, spec)

        # Check required files exist
        self.assertTrue((self.target / "MANIFESTO.md").exists())
        self.assertTrue((self.target / "ROADMAP.md").exists())
        self.assertTrue((self.target / "DECISIONS.md").exists())
        self.assertTrue((self.target / "AGENT_LOG.md").exists())
        self.assertTrue((self.target / "ralph.sh").exists())
        self.assertTrue((self.target / "tools" / "doctor.py").exists())
        self.assertTrue((self.target / "config" / "autoloop.json").exists())

        # Check doctor passes
        ok, results = run_doctor(self.target)
        self.assertTrue(ok, msg=f"Doctor failed with: {results}")


if __name__ == "__main__":
    unittest.main()
