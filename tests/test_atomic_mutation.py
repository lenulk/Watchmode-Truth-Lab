import contextlib
import errno
import io
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from test_file_worker import deny_read
from watchmode_truth_lab import cli, runner

ROOT = Path(__file__).resolve().parents[1]


def sharing_error(path, winerror=32):
    error = PermissionError(errno.EACCES, "sharing violation", str(path))
    error.winerror = winerror
    return error


def staged_files(target):
    return list(target.parent.glob(target.name + ".wtl-*"))


class AtomicMutationTests(unittest.TestCase):
    def test_transient_actual_sharing_denial_retries_and_replaces(self):
        with tempfile.TemporaryDirectory(prefix="atomic-mutation-", dir=ROOT / "reports") as temporary:
            target = Path(temporary) / "input.txt"
            target.write_bytes(b"seed")
            windows = os.name == "nt"
            release_handle = deny_read(target) if windows else None
            unlocked = threading.Event()
            observed_error = threading.Event()
            expedite_release = threading.Event()
            release_lock = threading.Lock()
            released = False
            errors = []
            original_replace = os.replace

            def unlock_once():
                nonlocal released
                with release_lock:
                    if released:
                        return
                    released = True
                if release_handle is not None:
                    release_handle()
                unlocked.set()

            def controlled_replace(source, destination):
                if not unlocked.is_set():
                    error = sharing_error(destination)
                    errors.append(error)
                    observed_error.set()
                    raise error
                return original_replace(source, destination)

            def observe_windows_replace(source, destination):
                try:
                    return original_replace(source, destination)
                except PermissionError as error:
                    errors.append(error)
                    observed_error.set()
                    raise

            def release_after_error():
                try:
                    if observed_error.wait(3) and not expedite_release.wait(0.25):
                        unlock_once()
                finally:
                    unlock_once()

            releaser = threading.Thread(target=release_after_error, daemon=True)
            releaser.start()
            try:
                if windows:
                    replacement = mock.patch.object(runner.os, "replace", observe_windows_replace)
                else:
                    replacement = mock.patch.object(
                        runner, "os", SimpleNamespace(name="nt", replace=controlled_replace))
                with replacement:
                    runner._mutate(target, b"updated", "atomic_replace")
                self.assertTrue(observed_error.is_set(), "Replacement was not denied while the read handle was held")
                self.assertTrue(errors, "The denied replacement error was not observed")
                self.assertEqual(target.read_bytes(), b"updated")
                self.assertEqual(staged_files(target), [])
                if windows:
                    self.assertTrue(all(error.errno == errno.EACCES and
                                        getattr(error, "winerror", None) in {5, 32} for error in errors), errors)
                else:
                    self.assertTrue(all(error.errno == errno.EACCES and error.winerror == 32 for error in errors), errors)
            finally:
                expedite_release.set()
                unlock_once()
                releaser.join(timeout=3)
                self.assertFalse(releaser.is_alive(), "Sharing handle release thread did not stop")

    def test_persistent_sharing_denial_is_bounded_and_preserves_target(self):
        with tempfile.TemporaryDirectory(prefix="atomic-mutation-", dir=ROOT / "reports") as temporary:
            target = Path(temporary) / "input.txt"
            target.write_bytes(b"seed")
            windows = os.name == "nt"
            release_handle = deny_read(target) if windows else None
            original_replace = os.replace

            def denied_replace(source, destination):
                raise sharing_error(destination, winerror=5)

            def observe_denial(source, destination):
                try:
                    return original_replace(source, destination)
                except PermissionError:
                    raise

            replacement = (mock.patch.object(runner.os, "replace", observe_denial) if windows else
                           mock.patch.object(runner, "os", SimpleNamespace(name="nt", replace=denied_replace)))
            started = time.monotonic()
            try:
                with replacement:
                    with self.assertRaises(PermissionError) as caught:
                        runner._mutate(target, b"updated", "atomic_replace")
                elapsed = time.monotonic() - started
                self.assertEqual(caught.exception.errno, errno.EACCES)
                self.assertGreaterEqual(elapsed, 0.8, "Persistent sharing denial was not retried")
                self.assertLess(elapsed, 2.5, "Persistent sharing denial exceeded its retry bound")
                if release_handle is not None:
                    release_handle()
                    release_handle = None
                self.assertEqual(target.read_bytes(), b"seed")
                self.assertEqual(staged_files(target), [])
            finally:
                if release_handle is not None:
                    release_handle()

    def test_unrelated_io_error_is_immediate_and_cleans_stage(self):
        with tempfile.TemporaryDirectory(prefix="atomic-mutation-", dir=ROOT / "reports") as temporary:
            target = Path(temporary) / "input.txt"
            target.write_bytes(b"seed")
            calls = []

            def unrelated_error(source, destination):
                calls.append((source, destination))
                raise OSError(errno.EIO, "controlled disk error", str(destination))

            started = time.monotonic()
            with mock.patch.object(runner, "os", SimpleNamespace(name="nt", replace=unrelated_error)):
                with self.assertRaises(OSError) as caught:
                    runner._mutate(target, b"updated", "atomic_replace")
            self.assertEqual(caught.exception.errno, errno.EIO)
            self.assertEqual(len(calls), 1, "Unrelated error was retried")
            self.assertLess(time.monotonic() - started, 0.5)
            self.assertEqual(target.read_bytes(), b"seed")
            self.assertEqual(staged_files(target), [])

    def test_cli_reports_mutation_failure_without_exposing_private_path(self):
        with tempfile.TemporaryDirectory(prefix="atomic-mutation-", dir=ROOT / "reports") as temporary:
            report_path = Path(temporary) / "result.json"
            private_path = str(Path(temporary) / "private-sentinel-do-not-report.txt")

            def denied_mutation(*args, **kwargs):
                raise sharing_error(private_path, winerror=32)

            stdout = io.StringIO()
            stderr = io.StringIO()
            argv = [str(ROOT / "example.json"), "--rounds", "1", "--mutation", "atomic_replace",
                    "--report", str(report_path)]
            with mock.patch.object(runner, "_mutate", side_effect=denied_mutation), \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    exit_code = cli.main(argv)
                except SystemExit as error:
                    self.fail(f"CLI raised SystemExit({error.code}) instead of recording mutation failure")
            self.assertEqual(exit_code, 1)
            self.assertTrue(report_path.is_file(), "CLI did not write the inconclusive report")
            serialized = report_path.read_text(encoding="utf-8")
            report = json.loads(serialized)
            self.assertEqual(report["status"], "inconclusive", report)
            self.assertEqual(len(report["attempts"]), 1, report)
            attempt = report["attempts"][0]
            self.assertEqual(attempt["status"], "inconclusive", attempt)
            self.assertEqual(attempt["reason"], "mutation_failed", attempt)
            self.assertEqual(attempt["mutation_error"],
                             {"type": "PermissionError", "errno": errno.EACCES, "winerror": 32}, attempt)
            self.assertNotIn(private_path, serialized)
            self.assertNotIn(private_path, stdout.getvalue())
            self.assertNotIn(private_path, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
