"""Retained acceptance controller for a selected wheel's documented first run."""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_cycle import ROOT, redact


class SelectedFileChecks(unittest.TestCase):
    def test_installed_console_first_run_and_file_mutations(self):
        executable = Path(os.environ["WTL_INSTALLED_PYTHON"]).absolute()
        project = Path(os.environ["WTL_FILE_PROJECT"]).resolve()
        output = (ROOT / os.environ["WTL_FILE_EVIDENCE"]).resolve()
        self.assertTrue(output.is_relative_to(ROOT / "evidence"))
        output.mkdir(parents=True, exist_ok=False)
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        console = executable.parent / ("watchmode-truth-lab.exe" if os.name == "nt" else "watchmode-truth-lab")
        original = (project / "fixture/input.txt").read_bytes()
        records = []
        identity_verified = False
        def invoke(arguments):
            result = subprocess.run([str(console), *arguments], cwd=project, env=environment,
                                    capture_output=True, text=True, encoding="utf-8", timeout=40)
            records.append({"arguments": arguments, "returncode": result.returncode,
                            "stdout": redact(result.stdout), "stderr": redact(result.stderr)})
            return result
        try:
            identity = subprocess.run([str(executable), "-c", "import watchmode_truth_lab,sys;from pathlib import Path;assert Path(watchmode_truth_lab.__file__).is_relative_to(Path(sys.prefix));print(watchmode_truth_lab.__version__)"],
                                      cwd=project, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(identity.returncode, 0, identity.stderr)
            self.assertEqual(identity.stdout.strip(), "1.0.0")
            identity_verified = True
            version = invoke(["--version"])
            self.assertEqual(version.returncode, 0, version.stderr)
            self.assertEqual(version.stdout.strip(), "watchmode-truth-lab 1.0.0")
            for action, expected in (("--validate", "valid"), ("--doctor", "ready")):
                result = invoke(["scenario.json", action])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], expected)
            for mode in ("overwrite", "atomic_replace", "burst"):
                with self.subTest(mutation=mode), tempfile.TemporaryDirectory(dir=ROOT / "reports") as temporary:
                    target = Path(temporary) / "result.json"
                    result = invoke(["scenario.json", "--rounds", "20", "--mutation", mode,
                                     "--format", "summary", "--report", str(target)])
                    report = json.loads(target.read_text(encoding="utf-8"))
                    (output / (mode + ".json")).write_text(redact(json.dumps(report, indent=2)) + "\n", encoding="utf-8")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(report["status"], "pass", report)
                    self.assertEqual(len(report["attempts"]), 20)
                    self.assertEqual(report["reproduction"]["argv"][0], str(executable))
            self.assertEqual((project / "fixture/input.txt").read_bytes(), original)
        finally:
            (output / "first-run.json").write_text(redact(json.dumps({"controller_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "import_within_fresh_venv_verified": identity_verified, "commands": records}, indent=2)) + "\n", encoding="utf-8")
