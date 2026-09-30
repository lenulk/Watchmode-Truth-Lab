"""Retain browser DOM freshness and HMR continuity evidence for each mutation."""

import argparse
import json
import os
import sys
import tempfile
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
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = []
    base = json.loads((ROOT / "vite.browser.json").read_text())
    cases = [(watcher, mode, args.rounds, "pass") for watcher in ("native", "polling")
             for mode in ("overwrite", "atomic_replace", "burst")]
    cases.append(("disabled", "overwrite", 1, "stale"))
    for watcher, mode, rounds, expected in cases:
        config = dict(base)
        config["fixture_dir"] = str(ROOT / base["fixture_dir"])
        for field in ("command", "version_command"):
            config[field] = [value.replace("{config_dir}", str(ROOT)) for value in base[field]]
        config["env"] = ({"WTL_USE_POLLING": "1"} if watcher == "polling" else
                         {"WTL_DISABLE_WATCH": "1"} if watcher == "disabled" else {})
        try:
            with tempfile.TemporaryDirectory() as temporary:
                scenario = Path(temporary) / f"vite.browser.{watcher}.json"
                scenario.write_text(json.dumps(config), encoding="utf-8")
                report = run(scenario, rounds=rounds, mutation=mode)
        except Exception:
            report = {"status": "error", "logs": [], "exception": redact(traceback.format_exc())}
        states = [json.loads(line.removeprefix("WTL_BROWSER_STATE ")) for line in report["logs"]
                  if line.startswith("WTL_BROWSER_STATE ")]
        versions = [line.removeprefix("WTL_BROWSER_VERSION ") for line in report["logs"]
                    if line.startswith("WTL_BROWSER_VERSION ")]
        continuity = bool(states) and len({state["session"] for state in states}) == 1
        updates = states[-1]["updates"] if states else None
        assessment = "pass" if report["status"] == expected and continuity and (
            updates >= rounds if expected == "pass" else updates == 0) else "fail"
        record = {"watcher": watcher, "mutation": mode, "expected_status": expected,
                  "browser_channel": os.environ.get("WTL_BROWSER_CHANNEL", "chrome"),
                  "assessment": assessment, "browser_version": versions, "session_continuity": continuity,
                  "observed_hmr_updates": updates, "scenario_base": "vite.browser.json", "scenario_env": config["env"],
                  "analysis": "Actual DOM token and a retained page session were observed. A disabled watcher is an expected stale control, not a newly discovered tool failure.",
                  "report": report}
        filename = f"{watcher}-{mode}.json"
        (args.output / filename).write_text(redact(json.dumps(record, indent=2)) + "\n", encoding="utf-8")
        summary.append({"file": filename, "status": report["status"], "assessment": assessment,
                        "session_continuity": continuity, "hmr_updates": updates})
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"Browser HMR {watcher} {mode}: {report['status']}; continuity={continuity}; saved {filename}", flush=True)
        if assessment == "fail":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
