import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CLIBoundaryTests(unittest.TestCase):
    def test_invalid_scenarios_use_configuration_exit_code(self):
        changes = [("missing_command", lambda c: c.pop("command")),
                   ("mutation_list", lambda c: c.update(mutation=[])),
                   ("oracle_type_list", lambda c: c["oracle"].update(type=[])),
                   ("impossible_stability", lambda c: c.update(stable_seconds=4, timeout_seconds=3))]
        for name, change in changes:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as temporary:
                config = json.loads((ROOT / "example.json").read_text(encoding="utf-8"))
                config["fixture_dir"] = str(ROOT / "examples" / "fixture")
                change(config)
                path = Path(temporary) / "invalid.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                result = subprocess.run([sys.executable, "-m", "watchmode_truth_lab", str(path)], cwd=ROOT,
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
