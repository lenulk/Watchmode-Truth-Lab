import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from watchmode_truth_lab.diagnostics import diagnose
from watchmode_truth_lab.starter import create_starter


class DiagnosticTests(unittest.TestCase):
    def test_file_ready_without_running_watch_or_version_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "demo"
            create_starter(project)
            with patch("watchmode_truth_lab.runner._launch") as launch:
                result = diagnose(project / "scenario.json")
            self.assertEqual(result["status"], "ready", result)
            launch.assert_not_called()
            self.assertFalse((project / "fixture/output.txt").exists())

    def test_missing_executable_and_node_assets_are_actionable(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "demo"
            create_starter(project, "vite-browser")
            path = project / "scenario.json"
            config = json.loads(path.read_text(encoding="utf-8"))
            config["command"][0] = "wtl-deliberately-missing-executable"
            path.write_text(json.dumps(config), encoding="utf-8")
            result = diagnose(path)
            self.assertEqual(result["status"], "not_ready")
            failures = {check["name"]: check["message"] for check in result["checks"] if check["status"] == "fail"}
            self.assertIn("command.executable", failures)
            self.assertIn("dependency.vite", failures)
            self.assertIn("browser", failures)
            self.assertIn("pnpm install", failures["dependency.vite"])
