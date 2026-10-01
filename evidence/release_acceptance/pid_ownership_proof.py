"""Controlled reproduction against the original PID-only snapshot algorithm."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evidence.release_acceptance.pid_only_snapshot import descendants


class OwnershipProof(unittest.TestCase):
    def test_reused_parent_pid_adopts_older_unrelated_processes(self):
        # Current root 100 was born at 50; child 200 at 60. Process 300
        # was born at 10 when an earlier process had PID 100, and 400 at 20.
        # Creation metadata is deliberately unavailable to the old algorithm.
        rows = [{"ProcessId": 100, "ParentProcessId": 1},
                {"ProcessId": 200, "ParentProcessId": 100},
                {"ProcessId": 300, "ParentProcessId": 100},
                {"ProcessId": 400, "ParentProcessId": 300}]
        with patch("os.name", "nt"), patch("subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(rows))):
            observed = descendants(100)
        self.assertEqual(observed, [200, 300, 400])
        self.assertNotEqual(observed, [200], "Old algorithm unexpectedly knows process birth identity")
