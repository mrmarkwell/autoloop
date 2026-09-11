#!/usr/bin/env python3
"""Hermetic unit tests for Autoloop Executive Summary & Project Overview engine."""

from pathlib import Path
import tempfile
import unittest

from tools.executive_summary import (
    BlockerInfo,
    CadenceInfo,
    ExecutiveReport,
    RoadmapStats,
    RunEntry,
    VCSInfo,
    detect_project_name,
    format_markdown_overview,
    format_markdown_report,
    format_overview,
    generate_summary,
    get_blocker_info,
    get_cadence_info,
    parse_agent_log,
    parse_roadmap,
    render_progress_bar,
)


class TestExecutiveSummary(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_render_progress_bar(self):
        self.assertEqual(render_progress_bar(0.0, width=10), '[░░░░░░░░░░]')
        self.assertEqual(render_progress_bar(100.0, width=10), '[██████████]')
        self.assertEqual(render_progress_bar(50.0, width=10), '[█████░░░░░]')

    def test_cadence_info_detection(self):
        runs = [RunEntry(run_number=i, title=f'Run {i}', date_str='2026-09-10') for i in range(1, 5)]
        cadence = get_cadence_info(runs)
        self.assertEqual(cadence.next_run, 5)
        self.assertIn('Cleanup Sprint', cadence.cadence_name)
        self.assertEqual(cadence.cadence_icon, '🧹')

        runs_9 = [RunEntry(run_number=i, title=f'Run {i}', date_str='2026-09-10') for i in range(1, 10)]
        cadence_10 = get_cadence_info(runs_9)
        self.assertEqual(cadence_10.next_run, 10)
        self.assertIn('Double Milestone', cadence_10.cadence_name)
        self.assertEqual(cadence_10.cadence_icon, '👑')

        runs_10 = [RunEntry(run_number=i, title=f'Run {i}', date_str='2026-09-10') for i in range(1, 11)]
        cadence_11 = get_cadence_info(runs_10)
        self.assertEqual(cadence_11.next_run, 11)
        self.assertIn('Standard Cycle', cadence_11.cadence_name)
        self.assertEqual(cadence_11.cadence_icon, '🚀')

    def test_blocker_info(self):
        # When BLOCKED.md does not exist
        info = get_blocker_info(self.root)
        self.assertFalse(info.is_blocked)
        self.assertIn('Unblocked', info.summary)

        # When BLOCKED.md exists with reason
        blocked_file = self.root / 'BLOCKED.md'
        blocked_file.write_text("# Blocked\nMissing API credential for external service.\n", encoding='utf-8')
        info_blocked = get_blocker_info(self.root)
        self.assertTrue(info_blocked.is_blocked)
        self.assertIn('Missing API credential', info_blocked.summary)

    def test_detect_project_name(self):
        # Test detection from MANIFESTO.md
        manifesto = self.root / 'MANIFESTO.md'
        manifesto.write_text("# AlphaEngine Manifesto\nCore vision\n", encoding='utf-8')
        name = detect_project_name(self.root)
        self.assertEqual(name, 'AlphaEngine')

    def test_format_overview_and_markdown(self):
        report = ExecutiveReport(
            start_run=1,
            end_run=3,
            run_count=3,
            runs=[
                RunEntry(run_number=1, title='Run 001', date_str='2026-09-10', task='Initial Scaffold'),
                RunEntry(run_number=2, title='Run 002', date_str='2026-09-10', task='Add Core Index'),
                RunEntry(run_number=3, title='Run 003', date_str='2026-09-10', task='Add Query API'),
            ],
            roadmap_stats=RoadmapStats(
                total_tasks=10,
                completed_tasks=3,
                in_progress_tasks=1,
                todo_tasks=6,
                active_phase='Phase 1: Foundation',
                phase_progress={'Phase 1: Foundation': (3, 5), 'Phase 2: Extension': (0, 5)},
            ),
            avg_velocity_tasks_per_run=1.0,
            estimated_runs_remaining=7,
            system_health_status='EXCELLENT',
            system_health_details=['[✓] Doc Sync', '[✓] Tests Pass'],
            project_name='TestApp',
            repo_root=str(self.root),
            vcs_info=VCSInfo(
                vcs_type='Git',
                branch='main',
                tracking='up to date with origin/main',
                clean=True,
                latest_commit='abc1234 — initial commit (1 hour ago)',
            ),
            blocker_info=BlockerInfo(is_blocked=False, summary='0 Blockers (Unblocked)'),
            cadence_info=CadenceInfo(total_runs=3, next_run=4, cadence_name='Standard Cycle', cadence_icon='🚀'),
        )

        overview_text = format_overview(report, use_color=False)
        self.assertIn('AUTOLOOP EXECUTIVE PROJECT OVERVIEW', overview_text)
        self.assertIn('TestApp', overview_text)
        self.assertIn('Clean', overview_text)
        self.assertIn('30.0%', overview_text)
        self.assertIn('Phase 1: Foundation', overview_text)
        self.assertIn('EXCELLENT', overview_text)

        md_overview = format_markdown_overview(report)
        self.assertIn('# Executive Summary & Trajectory Briefing — Whole Project Overview', md_overview)
        self.assertIn('Project: TestApp', md_overview)
        self.assertIn('Phase 1: Foundation', md_overview)

        md_report = format_markdown_report(report)
        self.assertIn('# Executive Summary & Trajectory Briefing (Runs #001 – #003)', md_report)
        self.assertIn('TestApp', md_report)


if __name__ == '__main__':
    unittest.main()
