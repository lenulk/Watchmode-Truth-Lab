"""Analyze a required CI cycle and reject skips, empty runs or stale source identity."""

import argparse
import json
import os
from pathlib import Path
from test_cycle import normalize_label

ROOT = Path(__file__).resolve().parents[1]


def find_record(directory, label):
    records = [path for path in directory.glob("*-" + normalize_label(label) + "-*.json")
               if not path.name.endswith("-analysis.json")]
    return max(records, key=lambda path: path.name) if records else None


def assess(report, minimum=1, revision=None):
    problems = []
    if report.get("status") != "pass" or report.get("failures") != 0 or report.get("errors") != 0:
        problems.append("Test failures or errors require investigation before the next gate")
    if report.get("skips") != 0:
        problems.append("Required tests were skipped; provision their dependencies and rerun")
    if report.get("tests_run", 0) < minimum:
        problems.append("Required test collection is missing or unexpectedly small")
    if revision and report.get("git_revision") != revision:
        problems.append("Recorded source revision does not match the CI commit")
    return {"assessment": "fail" if problems else "pass", "problems": problems,
            "analysis": "Required checks ran without skips/failures and met source/collection gates; this verifies the tested workflow, not absence of all bugs." if not problems else "Keep the failed evidence and resolve the listed gate before acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--minimum", type=int, default=1)
    args = parser.parse_args()
    source = find_record(ROOT / "evidence/test-runs", args.label)
    if source is None:
        parser.error("No saved cycle matches the required label")
    report = json.loads(source.read_text(encoding="utf-8"))
    result = {"source": source.name, **assess(report, args.minimum, os.environ.get("GITHUB_SHA"))}
    target = source.with_name(source.stem + "-analysis.json")
    if target.exists():
        parser.error("Analysis already exists; retain it and use a new cycle label")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["assessment"] + ": " + result["analysis"])
    for problem in result["problems"]:
        print(problem)
    return 0 if result["assessment"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
