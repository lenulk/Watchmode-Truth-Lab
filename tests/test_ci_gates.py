import unittest
import tempfile
from pathlib import Path

from ci_verify import assess, find_record
from test_cycle import normalize_label


class CIGateTests(unittest.TestCase):
    def test_record_lookup_matches_recorder_normalization_for_python_versions(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            label = "ci-core-ubuntu-latest-3.10"
            source = directory / ("20261001T000000Z-" + normalize_label(label) + "-abcdef.json")
            source.write_text("{}")
            source.with_name(source.stem + "-analysis.json").write_text("{}")
            (directory / "20261001T000001Z-other-label-abcdef.json").write_text("{}")
            self.assertEqual(find_record(directory, label), source)
            self.assertIsNone(find_record(directory, "missing"))

    def test_required_gate_rejects_skip_empty_failure_and_wrong_revision(self):
        base = {"status": "pass", "tests_run": 4, "failures": 0, "errors": 0, "skips": 0, "git_revision": "current"}
        for change in ({"skips": 1}, {"tests_run": 0}, {"status": "fail", "failures": 1}, {"git_revision": "old"}):
            with self.subTest(change=change):
                result = assess({**base, **change}, minimum=4, revision="current")
                self.assertEqual(result["assessment"], "fail")
                self.assertTrue(result["problems"])

    def test_complete_required_gate_keeps_observation_limits(self):
        result = assess({"status": "pass", "tests_run": 4, "failures": 0, "errors": 0, "skips": 0, "git_revision": "current"}, 4, "current")
        self.assertEqual(result["assessment"], "pass")
        self.assertIn("not absence of all bugs", result["analysis"])
