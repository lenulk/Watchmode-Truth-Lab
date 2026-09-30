"""Controlled time/process simulations for decisions that can cause false passes."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from watchmode_truth_lab.runner import _wait


class OracleDecisionTests(unittest.TestCase):
    def test_pending_response_after_match_cannot_pass_deadline(self):
        process = SimpleNamespace(poll=lambda: None)
        with patch("watchmode_truth_lab.runner._read_output", side_effect=[(b"new", None), (None, "probe_pending")]), \
                patch("watchmode_truth_lab.runner.time.monotonic", side_effect=[0, 0, 0.01, 0.01, 0.2, 0.2]), \
                patch("watchmode_truth_lab.runner.time.sleep"):
            result = _wait(b"new", {}, Path("."), process, 0.1, 0.01, 0.05)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["reason"], "observation_deadline_exceeded")

    def test_matching_output_from_exited_process_is_inconclusive(self):
        process = SimpleNamespace(poll=lambda: 0, returncode=0)
        with patch("watchmode_truth_lab.runner._read_output", return_value=(b"new", None)):
            result = _wait(b"new", {}, Path("."), process, 1, 0.01, 0)
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["reason"], "process_exited_0")

    def test_matching_output_observed_after_deadline_is_timeout(self):
        process = SimpleNamespace(poll=lambda: None)
        with patch("watchmode_truth_lab.runner._read_output", return_value=(b"new", None)), \
                patch("watchmode_truth_lab.runner.time.monotonic", side_effect=[0, 0, 0.2, 0.2]):
            result = _wait(b"new", {}, Path("."), process, 0.1, 0.01, 0)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["reason"], "observation_deadline_exceeded")

    def test_transient_match_does_not_hide_final_stale_output(self):
        process = SimpleNamespace(poll=lambda: None)
        with patch("watchmode_truth_lab.runner._read_output", side_effect=[(b"new", None), (b"old", None)]), \
                patch("watchmode_truth_lab.runner.time.monotonic", side_effect=[0, 0, 0.01, 0.01, 0.2, 0.2]), \
                patch("watchmode_truth_lab.runner.time.sleep"):
            result = _wait(b"new", {}, Path("."), process, 0.1, 0.01, 0.05)
        self.assertEqual(result["status"], "stale")
