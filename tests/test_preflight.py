import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from watchmode_truth_lab import runner

ROOT = Path(__file__).resolve().parents[1]


class PreflightTests(unittest.TestCase):
    def test_prepare_never_starts_commands_allocates_workspace_or_mutates(self):
        source = ROOT / "examples/fixture/input.txt"
        before = source.read_bytes()
        with patch.object(runner, "_launch") as launch, \
                patch.object(runner, "_run_captured") as version, \
                patch.object(runner.tempfile, "TemporaryDirectory") as workspace, \
                patch.object(runner.socket, "socket") as socket:
            for name in ("example.json", "vite.native.json", "vite.browser.json"):
                self.assertTrue(runner.prepare_scenario(ROOT / name)["fixture"].is_dir())
            for operation in (launch, version, workspace, socket):
                operation.assert_not_called()
        self.assertEqual(source.read_bytes(), before)

    def test_invalid_late_fields_are_rejected_before_workspace_or_command(self):
        changes = [lambda c: c.update(version_command=[]), lambda c: c.update(env={"BAD=KEY": "x"}),
                   lambda c: c.update(command=[""]), lambda c: c.update(command=["python\0"]),
                   lambda c: c.update(mutation_target="../input.txt"),
                   lambda c: c["oracle"].update(path="../output.txt")]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "scenario.json"
            for change in changes:
                config = json.loads((ROOT / "example.json").read_text(encoding="utf-8"))
                config["fixture_dir"] = str(ROOT / "examples/fixture")
                change(config)
                path.write_text(json.dumps(config), encoding="utf-8")
                with self.subTest(config=config), patch.object(runner, "_launch") as launch, \
                        patch.object(runner.tempfile, "TemporaryDirectory") as workspace:
                    with self.assertRaises(runner.ConfigError):
                        runner.run(path)
                    launch.assert_not_called()
                    workspace.assert_not_called()

    def test_cli_validate_does_not_execute_scenario_or_version_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "executed.txt"
            config = json.loads((ROOT / "example.json").read_text(encoding="utf-8"))
            config["fixture_dir"] = str(ROOT / "examples/fixture")
            config["command"] = config["version_command"] = [sys.executable, "-c", f"open({str(marker)!r},'w').write('executed')"]
            path = root / "scenario.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "watchmode_truth_lab", str(path), "--validate"],
                                    cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "valid")
            self.assertFalse(marker.exists())
