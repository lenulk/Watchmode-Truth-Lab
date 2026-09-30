"""Verify installed Vite starters; environment selects isolated Python/project/evidence."""

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_cycle import ROOT, redact


class InstalledWorkflowChecks(unittest.TestCase):
    def test_installed_vite_watchers_mutations_and_disabled_control(self):
        executable = Path(os.environ["WTL_INSTALLED_PYTHON"]).absolute()
        project = Path(os.environ["WTL_WORKFLOW_PROJECT"]).resolve()
        output = (ROOT / os.environ["WTL_WORKFLOW_EVIDENCE"]).resolve()
        self.assertTrue(output.is_relative_to(ROOT / "evidence"))
        output.mkdir(parents=True, exist_ok=False)
        rounds = int(os.environ.get("WTL_WORKFLOW_ROUNDS", "20"))
        original = hashlib.sha256((project / "fixture/src/token.js").read_bytes()).hexdigest()
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        doctor = subprocess.run([str(executable), "-m", "watchmode_truth_lab", "scenario.json", "--doctor"],
                                cwd=project, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=25)
        (output / "doctor.json").write_text(redact(doctor.stdout) if doctor.stdout else json.dumps({"error": redact(doctor.stderr)}), encoding="utf-8")
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
        summary = []
        cases = [(name, mode, rounds, "pass") for name in ("scenario", "polling")
                 for mode in ("overwrite", "atomic_replace", "burst")]
        cases.append(("disabled", "overwrite", 1, "stale"))
        for name, mode, repetitions, expected in cases:
            with tempfile.TemporaryDirectory(dir=ROOT / "reports") as temporary:
                target = Path(temporary) / "report.json"
                result = subprocess.run([str(executable), "-m", "watchmode_truth_lab", name + ".json", "--rounds", str(repetitions),
                                         "--mutation", mode, "--report", str(target)],
                                        cwd=project, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=180)
                report = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {"status": "error", "logs": [], "diagnostic": result.stdout + result.stderr}
            states = [json.loads(line.removeprefix("WTL_BROWSER_STATE ")) for line in report.get("logs", []) if line.startswith("WTL_BROWSER_STATE ")]
            browser = any(part.endswith("browser_probe.mjs") for part in report.get("command", []))
            continuity = bool(states) and len({state["session"] for state in states}) == 1
            state_retained = bool(states) and all(state.get("retainedState") == "1" for state in states)
            updated = states[-1]["updates"] if states else None
            passed = report["status"] == expected and result.returncode == (0 if expected == "pass" else 1)
            if browser:
                passed &= continuity and state_retained and (updated >= repetitions if expected == "pass" else updated == 0)
            filename = name + "-" + mode + ".json"
            record = {"expected_status": expected, "assessment": "pass" if passed else "fail",
                      "installed_python": "isolated venv outside source checkout", "browser_engine": environment.get("WTL_BROWSER_ENGINE", "chromium") if browser else None,
                      "session_continuity": continuity if browser else None, "application_state_retained": state_retained if browser else None,
                      "observed_updates": updated, "update_metric": states[-1].get("updateMetric") if states else None,
                      "analysis": "Installed starter with real Vite, isolated fixture mutation and disabled watcher control; DOM counts are sampled changes, not framework callback counts.", "report": report}
            (output / filename).write_text(redact(json.dumps(record, indent=2)) + "\n", encoding="utf-8")
            summary.append({"file": filename, "status": report["status"], "assessment": record["assessment"]})
            (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            self.assertTrue(passed, redact(json.dumps(record, indent=2)))
        self.assertEqual(hashlib.sha256((project / "fixture/src/token.js").read_bytes()).hexdigest(), original)
