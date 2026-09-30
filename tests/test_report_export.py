import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from watchmode_truth_lab import cli
from watchmode_truth_lab import reporting

ROOT = Path(__file__).resolve().parents[1]


class ReportExportTests(unittest.TestCase):
    def test_interrupted_report_write_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "result.json"
            report.write_bytes(b'{"previous": true}\n')
            def fail_write(stream, content):
                stream.write(content[:5])
                raise OSError("simulated interrupted report write")

            with patch.object(cli, "run", return_value={"status": "pass"}), \
                    patch.object(reporting, "_write_content", side_effect=fail_write) as fault, \
                    contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                try:
                    cli.main([str(ROOT / "example.json"), "--report", str(report)])
                except SystemExit as exc:
                    self.assertEqual(exc.code, 2)
            fault.assert_called_once()
            self.assertEqual(report.read_bytes(), b'{"previous": true}\n')
            self.assertEqual({path.name for path in Path(temporary).iterdir()}, {"result.json"})

    def test_replace_failure_preserves_original_and_removes_temporary(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "result.json"
            report.write_bytes(b"previous")
            with patch.object(reporting.os, "replace", side_effect=PermissionError("locked")) as fault:
                with self.assertRaises(PermissionError):
                    reporting.write_report(report, '{"status":"pass"}')
                fault.assert_called_once()
            self.assertEqual(report.read_bytes(), b"previous")
            self.assertEqual({path.name for path in Path(temporary).iterdir()}, {"result.json"})

    def test_successful_summary_keeps_json_export_and_existing_default(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "result.json"
            result = {"status": "stale", "startup": {"status": "pass"},
                      "attempts": [{"round": 1, "status": "stale", "reason": "output_mismatch"}]}
            output = io.StringIO()
            with patch.object(cli, "run", return_value=result), contextlib.redirect_stdout(output):
                code = cli.main([str(ROOT / "example.json"), "--format", "summary", "--report", str(report)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8")), result)
            self.assertIn("Round 1: stale (output_mismatch)", output.getvalue())
            output = io.StringIO()
            with patch.object(cli, "run", return_value=result), contextlib.redirect_stdout(output):
                self.assertEqual(cli.main([str(ROOT / "example.json")]), 1)
            self.assertEqual(json.loads(output.getvalue()), result)
