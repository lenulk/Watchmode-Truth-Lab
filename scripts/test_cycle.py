"""Run unittest and persist outcomes even when the suite fails."""

import argparse
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def redact(text):
    for value, replacement in ((str(ROOT), "<project>"), (str(Path.home()), "<home>")):
        # Match mixed separators and paths escaped more than once inside JSON logs.
        pattern = r"[\\/]+".join(re.escape(part) for part in re.split(r"[\\/]", value))
        text = re.sub(pattern, lambda match: replacement, text)
    return text


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []
        self.started = {}

    def startTest(self, test):
        self.started[test.id()] = time.monotonic()
        super().startTest(test)

    def record(self, test, status, detail=None):
        self.cases.append({"test": test.id(), "status": status,
                           "duration_seconds": round(time.monotonic() - self.started.get(test.id(), time.monotonic()), 4),
                           "detail": redact(detail) if detail else None})

    def addSuccess(self, test):
        self.record(test, "pass")
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.record(test, "fail", self._exc_info_to_string(err, test))
        super().addFailure(test, err)

    def addError(self, test, err):
        self.record(test, "error", self._exc_info_to_string(err, test))
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.record(test, "skip", reason)
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.record(subtest, "fail", self._exc_info_to_string(err, test))
        super().addSubTest(test, subtest, err)


def git_value(*args):
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--test", action="append", help="Specific unittest test name; may be repeated")
    args = parser.parse_args()
    timestamp = datetime.now(timezone.utc)
    label = re.sub(r"[^a-zA-Z0-9_-]", "-", args.label)
    run_id = timestamp.strftime("%Y%m%dT%H%M%SZ") + "-" + label + "-" + uuid.uuid4().hex[:6]
    output = ROOT / "evidence" / "test-runs"
    output.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO()
    suite = (unittest.defaultTestLoader.loadTestsFromNames(args.test) if args.test else
             unittest.defaultTestLoader.discover(str(ROOT / "tests")))
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(suite)
    git_status = git_value("status", "--porcelain")
    report = {"schema_version": 1, "run_id": run_id, "started_at_utc": timestamp.isoformat(),
              "purpose": args.purpose, "git_revision": git_value("rev-parse", "HEAD") or os.environ.get("WTL_SOURCE_REVISION"),
              "working_tree_dirty": None if git_status is None else bool(git_status),
              "recorder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256((ROOT / "watchmode_truth_lab/runner.py").read_bytes()).hexdigest(),
              "environment": {"system": platform.system(), "release": platform.release(),
                              "python": platform.python_version()},
              "duration_seconds": round(time.monotonic() - started, 3),
              "status": "pass" if result.wasSuccessful() else "fail", "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
              "cases": result.cases}
    (output / (run_id + ".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / (run_id + ".log")).write_text(redact(stream.getvalue()), encoding="utf-8")
    print(f"{report['status']}: {result.testsRun} tests, {report['failures']} failures, "
          f"{report['errors']} errors, {report['skips']} skips")
    print(f"Saved evidence/test-runs/{run_id}.json and .log")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
