import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import scenario_cycle
import test_cycle


class RecordingTests(unittest.TestCase):
    def test_git_unicode_checkout_path_is_captured(self):
        (test_cycle.ROOT / "reports").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="git-ทดสอบ-", dir=test_cycle.ROOT / "reports") as temporary:
            root = Path(temporary).resolve()
            result = subprocess.run(["git", "init", str(root)], capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            with patch.object(test_cycle, "ROOT", root):
                path = test_cycle.git_value("rev-parse", "--show-toplevel")
            self.assertEqual(path, root.as_posix())

    def test_missing_git_returns_unknown_metadata(self):
        with patch.object(test_cycle.subprocess, "run", side_effect=FileNotFoundError("git missing")):
            self.assertIsNone(test_cycle.git_value("rev-parse", "HEAD"))

    def test_source_identity_detects_temporary_source_change_and_ignores_generated_paths(self):
        with tempfile.TemporaryDirectory(prefix="source-identity-") as temporary:
            root = Path(temporary)
            source = root / "watchmode_truth_lab" / "assets" / "vite" / "main.js"
            source.parent.mkdir(parents=True)
            source.write_text("export const token = 'before';\n", encoding="utf-8")
            (root / "example.json").write_text('{"scenario": true}\n', encoding="utf-8")
            for excluded in ("docs", "evidence", "reports", "node_modules", "__pycache__"):
                path = root / excluded / "generated.txt"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("generated", encoding="utf-8")

            before = test_cycle.source_identity(root)
            source.write_text("export const token = 'after';\n", encoding="utf-8")
            after = test_cycle.source_identity(root)

            self.assertIsNone(before["git_revision"])
            self.assertIsNone(after["git_revision"])
            self.assertEqual(set(before["files_sha256"]), {"example.json", "watchmode_truth_lab/assets/vite/main.js"})
            self.assertEqual(set(after["files_sha256"]), set(before["files_sha256"]))
            changed = [name for name in before["files_sha256"]
                       if before["files_sha256"][name] != after["files_sha256"][name]]
            self.assertEqual(changed, ["watchmode_truth_lab/assets/vite/main.js"])

    def test_existing_matrix_directory_is_rejected_before_scenarios(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "saved"
            output.mkdir()
            marker = output / "summary.json"
            marker.write_text('[{"original": true}]', encoding="utf-8")
            with patch("sys.argv", ["scenario_cycle.py", "--output", str(output), "--label", "test"]), \
                    patch.object(scenario_cycle, "run", return_value={"status": "pass"}) as run:
                with self.assertRaises(FileExistsError):
                    scenario_cycle.main()
                run.assert_not_called()
            self.assertEqual(marker.read_text(encoding="utf-8"), '[{"original": true}]')
