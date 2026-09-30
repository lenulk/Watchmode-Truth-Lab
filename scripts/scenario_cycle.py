"""Run and retain a real Vite matrix, including an expected-stale control."""

import argparse
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from test_cycle import redact
from watchmode_truth_lab.runner import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = [("vite.native.json", mode, "pass", args.rounds) for mode in ("overwrite", "atomic_replace", "burst")]
    cases += [("vite.polling.json", mode, "pass", args.rounds) for mode in ("overwrite", "atomic_replace", "burst")]
    cases += [("vite.disabled.json", "overwrite", "stale", 1)]
    assessments = []
    for scenario, mode, expected, rounds in cases:
        path = args.output / (scenario.replace(".json", "") + "-" + mode + ".json")
        try:
            report = run(ROOT / scenario, rounds=rounds, mutation=mode)
        except Exception:
            report = {"status": "error", "exception": redact(traceback.format_exc())}
        assessment = "pass" if report["status"] == expected else "fail"
        analysis = ("Expected latest output was observed for every round under the scenario time policy."
                    if expected == "pass" else "Deliberately disabled watcher was correctly detected as stale; this is a control, not a tool bug.")
        if assessment == "fail":
            analysis = "Observed outcome differs from the control expectation; inspect this report before drawing conclusions."
        record = {"label": args.label, "scenario": scenario, "mutation": mode, "expected_status": expected,
                  "assessment": assessment, "analysis": analysis, "report": report}
        path.write_text(redact(json.dumps(record, ensure_ascii=False, indent=2)) + "\n", encoding="utf-8")
        assessments.append({"file": path.name, "status": report["status"], "assessment": assessment})
        (args.output / "summary.json").write_text(json.dumps(assessments, indent=2) + "\n", encoding="utf-8")
        print(f"{scenario} {mode}: {report['status']} (expected {expected}); saved {path.name}", flush=True)
        if assessment == "fail":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
