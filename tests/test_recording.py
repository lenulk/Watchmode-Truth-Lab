import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scenario_cycle


class RecordingTests(unittest.TestCase):
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
