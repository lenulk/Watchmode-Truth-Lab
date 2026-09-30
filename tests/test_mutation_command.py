import json
import tempfile
import unittest
from pathlib import Path

from watchmode_truth_lab.runner import run

ROOT = Path(__file__).resolve().parents[1]


class MutationCommandTests(unittest.TestCase):
    def test_noisy_mutator_and_timeout_are_bounded(self):
        for timeout_case in (False, True):
            with self.subTest(timeout=timeout_case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                worker = root / "mutate.py"
                worker.write_text("import base64,pathlib,sys,time\n"
                                  "print('x' * (2 * 1024 * 1024), flush=True)\n"
                                  + ("time.sleep(10)\n" if timeout_case else
                                     "pathlib.Path(sys.argv[1]).write_bytes(base64.b64decode(sys.argv[2]))\n"),
                                  encoding="utf-8")
                config = json.loads((ROOT / "example.json").read_text())
                config["fixture_dir"] = str(ROOT / "examples" / "fixture")
                config["command"][1] = str(ROOT / "examples" / "polling_generator.py")
                config["mutation_command"] = ["{python}", str(worker), "{target}", "{content_base64}"]
                config["mutation_timeout_seconds"] = 0.3 if timeout_case else 3
                path = root / "scenario.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                result = run(path)
                self.assertEqual(result["status"], "inconclusive" if timeout_case else "pass", result)
                info = result["attempts"][0]["mutation_command_result"]
                self.assertLessEqual(len(info["diagnostics"]), 2000)
                if timeout_case:
                    self.assertIsNone(info["returncode"])
                    self.assertEqual(info["reason"], "mutation_deadline_exceeded")

    def test_external_mutation_success_and_failure_are_distinguished(self):
        for code in (0, 9):
            with self.subTest(returncode=code), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                worker = root / "mutate.py"
                worker.write_text("import base64,pathlib,sys\n"
                                  "pathlib.Path(sys.argv[1]).write_bytes(base64.b64decode(sys.argv[2]))\n"
                                  "sys.exit(int(sys.argv[3]))\n", encoding="utf-8")
                config = json.loads((ROOT / "example.json").read_text())
                config["fixture_dir"] = str(ROOT / "examples" / "fixture")
                config["command"][1] = str(ROOT / "examples" / "polling_generator.py")
                config["mutation_command"] = ["{python}", str(worker), "{target}", "{content_base64}", str(code)]
                path = root / "scenario.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                result = run(path)
                self.assertEqual(result["status"], "pass" if code == 0 else "inconclusive", result)
                self.assertEqual(result["attempts"][0]["mutation_command_result"]["returncode"], code)
                if code:
                    self.assertEqual(result["attempts"][0]["reason"], "mutation_command_failed")
