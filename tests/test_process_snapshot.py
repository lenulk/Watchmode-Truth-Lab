import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.process_snapshot import descendants, identity, is_alive, select_descendants, terminate_observed


class ProcessSnapshotTests(unittest.TestCase):
    def test_recycled_parent_excludes_older_branch_and_cycle(self):
        rows = [{"pid": 100, "parent_pid": 400, "created": 50},
                {"pid": 200, "parent_pid": 100, "created": 60},
                {"pid": 300, "parent_pid": 100, "created": 10},
                {"pid": 400, "parent_pid": 300, "created": 20},
                {"pid": 500, "parent_pid": 200, "created": 70}]
        self.assertEqual([row["pid"] for row in select_descendants(100, rows)], [200, 500])
        with self.assertRaises(RuntimeError):
            select_descendants(999, rows)

    def test_liveness_rejects_reused_pid(self):
        recorded = {"pid": 100, "created": 50}
        with patch("scripts.process_snapshot.identity", return_value={"pid": 100, "created": 60}):
            self.assertFalse(is_alive(recorded))
        with patch("scripts.process_snapshot.identity", return_value=None):
            self.assertFalse(is_alive(recorded))

    def test_query_error_does_not_claim_process_exited(self):
        with patch("scripts.process_snapshot.identity", side_effect=PermissionError("controlled query failure")):
            with self.assertRaises(PermissionError):
                is_alive({"pid": 100, "created": 50})

    def test_actual_child_identity_and_safe_termination(self):
        child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
        try:
            record = identity(child.pid)
            self.assertIsNotNone(record)
            observed = descendants(os.getpid())
            self.assertIn(child.pid, [row["pid"] for row in observed])
            self.assertEqual(next(row["created"] for row in observed if row["pid"] == child.pid), record["created"])
            terminate_observed(dict(record, created=record["created"] + 1))
            self.assertTrue(is_alive(record), "Cleanup killed a mismatched process generation")
            terminate_observed(record)
            child.wait(timeout=5)
            self.assertFalse(is_alive(record))
        finally:
            if child.poll() is None:
                child.kill()  # Popen owns its stable process handle.
            child.wait(timeout=5)
