import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from watchmode_truth_lab.diagnostics import diagnose
from watchmode_truth_lab.starter import create_starter


class DiagnosticTests(unittest.TestCase):
    def test_malformed_dependency_metadata_is_not_ready_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "demo"
            create_starter(project, "vite-http")
            manifest = project / "package.json"
            for metadata in ([], {"devDependencies": []}, {"devDependencies": {"vite": None}}):
                with self.subTest(metadata=metadata):
                    manifest.write_text(json.dumps(metadata), encoding="utf-8")
                    result = diagnose(project / "scenario.json")
                    self.assertEqual(result["status"], "not_ready")
                    self.assertTrue(any(check["name"].startswith("manifest") and check["status"] == "fail"
                                        for check in result["checks"]))
            manifest.write_text(json.dumps({"devDependencies": {"vite": "8.3.1"}}), encoding="utf-8")
            installed = project / "node_modules/vite/package.json"
            installed.parent.mkdir(parents=True)
            installed.write_text("[]", encoding="utf-8")
            result = diagnose(project / "scenario.json")
            self.assertEqual(result["status"], "not_ready")
            self.assertTrue(any(check["name"] == "dependency.vite" and check["status"] == "fail"
                                for check in result["checks"]))

    def test_dependency_range_is_not_mistaken_for_an_exact_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "demo"
            create_starter(project, "vite-http")
            (project / "package.json").write_text(json.dumps({"devDependencies": {"vite": "8.x"}}), encoding="utf-8")
            installed = project / "node_modules/vite/package.json"
            installed.parent.mkdir(parents=True)
            installed.write_text(json.dumps({"version": "8.3.1"}), encoding="utf-8")
            result = diagnose(project / "scenario.json")
            dependency = next(check for check in result["checks"] if check["name"] == "dependency.vite")
            self.assertEqual(dependency["status"], "pass")
            self.assertIn("range compatibility not verified", dependency["message"])

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
