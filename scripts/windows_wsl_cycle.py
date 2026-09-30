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
    parser = argparse.ArgumentParser(description="Measure Windows-process mutations of WSL2 Linux fixtures")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--workspace-parent", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = []
    for watcher in ("native", "polling"):
        original = json.loads((ROOT / f"vite.{watcher}.json").read_text())
        original["mutation_command"] = ["{python}", "{config_dir}/scripts/windows_wsl_mutator.py", "{workspace}",
                                        "{target}", "{mode}", "{content_base64}", "{intermediate_base64}"]
        original["mutation_timeout_seconds"] = 15
        original["startup_timeout_seconds"] = 8
        original["timeout_seconds"] = 2
        if args.workspace_parent:
            original["workspace_parent"] = str(args.workspace_parent)
        scenario = ROOT / f"vite.windows-origin.{watcher}.json"
        scenario.write_text(json.dumps(original, indent=2), encoding="utf-8")
        for mode in ("overwrite", "atomic_replace", "burst"):
            try:
                report = run(scenario, rounds=args.rounds, mutation=mode)
            except Exception:
                report = {"status": "error", "attempts": [], "exception": redact(traceback.format_exc())}
            access = "Windows NTFS mounted in WSL2" if args.workspace_parent else "WSL2 UNC share to Linux filesystem"
            record = {"mutation_origin": "Windows PowerShell process", "access_path": access,
                      "scenario": scenario.name, "mutation": mode,
                      "analysis": "Observed freshness is specific to the recorded origin and filesystem path. A native stale result must be compared with documented WSL2 limitations; browser HMR is not covered.",
                      "report": report}
            filename = f"{watcher}-{mode}.json"
            (args.output / filename).write_text(redact(json.dumps(record, indent=2)) + "\n", encoding="utf-8")
            summary.append({"file": filename, "status": report["status"], "rounds": len(report["attempts"])})
            (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"Windows -> WSL2 {access} {watcher} {mode}: {report['status']}; saved {filename}", flush=True)
            if report["status"] in {"inconclusive", "timeout", "error"}:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
