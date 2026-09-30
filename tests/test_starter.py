import json
import tempfile
import unittest
from pathlib import Path

from watchmode_truth_lab.runner import ConfigError, prepare_scenario, run
from watchmode_truth_lab.starter import TEMPLATES, create_starter


class StarterTests(unittest.TestCase):
    def test_all_templates_include_valid_config_and_required_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            for template in TEMPLATES:
                with self.subTest(template=template):
                    destination = Path(temporary) / template
                    create_starter(destination, template)
                    scenario = prepare_scenario(destination / "scenario.json")
                    self.assertTrue(scenario["fixture"].is_dir())
                    if template != "file":
                        for name in ("polling.json", "disabled.json"):
                            prepare_scenario(destination / name)
                        package = json.loads((destination / "package.json").read_text(encoding="utf-8"))
                        self.assertEqual(package["devDependencies"]["vite"], "8.3.1")
                        self.assertTrue((destination / "pnpm-lock.yaml").is_file())
                        self.assertTrue((destination / "fixture/src/main.js").is_file())
                        self.assertTrue((destination / "browser_probe.mjs").is_file())

    def test_file_starter_runs_without_source_checkout_assets(self):
        with tempfile.TemporaryDirectory(prefix="starter space-") as temporary:
            destination = Path(temporary) / "demo"
            create_starter(destination)
            original = (destination / "fixture/input.txt").read_bytes()
            for mode in ("overwrite", "atomic_replace", "burst"):
                result = run(destination / "scenario.json", rounds=2, mutation=mode)
                self.assertEqual(result["status"], "pass", result)
            self.assertEqual((destination / "fixture/input.txt").read_bytes(), original)
            self.assertFalse((destination / "fixture/output.txt").exists())

    def test_existing_work_is_retained_and_failed_stage_is_cleaned(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            existing = parent / "existing"
            existing.mkdir()
            (existing / "marker").write_bytes(b"keep")
            with self.assertRaises(ConfigError):
                create_starter(existing)
            self.assertEqual((existing / "marker").read_bytes(), b"keep")
            with self.assertRaises(ConfigError):
                create_starter(parent / "invalid", "invalid")
            self.assertEqual({path.name for path in parent.iterdir()}, {"existing"})
