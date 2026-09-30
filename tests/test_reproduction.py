import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from watchmode_truth_lab.runner import run
from watchmode_truth_lab.starter import create_starter


class ReproductionTests(unittest.TestCase):
    def test_special_filename_reproduction_executes_with_original_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            create_starter(project)
            path = project / "scenario space's $token ü.json"
            (project / "scenario.json").rename(path)
            report = run(path)
            reproduction = report["reproduction"]
            argv = [sys.executable, "-m", "watchmode_truth_lab", path.name, "--rounds", "1", "--mutation", "overwrite"]
            self.assertEqual(reproduction["argv"], argv)
            environment = os.environ.copy()
            environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
            environment["PYTHONUTF8"] = "1"
            if os.name == "nt":
                self.assertEqual(reproduction["cli_shell"], "powershell")
                command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", reproduction["cli"]]
            else:
                self.assertEqual(reproduction["cli_shell"], "posix")
                self.assertEqual(shlex.split(reproduction["cli"]), argv)
                command = [shutil.which("sh"), "-c", reproduction["cli"]]
            result = subprocess.run(command, cwd=project, env=environment, capture_output=True,
                                    text=True, encoding="utf-8", timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            repeated = json.loads(result.stdout)
            self.assertEqual(repeated["config"], path.name)
            self.assertEqual(repeated["status"], "pass")
