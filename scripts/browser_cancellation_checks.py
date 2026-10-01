"""Installed controlled cancellation after a real browser becomes observable."""

import json
import os
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path

import process_snapshot
from process_snapshot import descendants, is_alive, terminate_observed
from test_cycle import ROOT


class BrowserCancellationChecks(unittest.TestCase):
    def test_installed_browser_interrupt_cleans_observed_process_tree(self):
        executable = Path(os.environ["WTL_INSTALLED_PYTHON"]).absolute()
        project = Path(os.environ["WTL_BROWSER_PROJECT"]).resolve()
        with tempfile.TemporaryDirectory(prefix="browser-cancel-", dir=ROOT / "reports") as temporary:
            root = Path(temporary)
            workspaces = root / "workspaces"
            workspaces.mkdir()
            config = json.loads((project / "scenario.json").read_text(encoding="utf-8"))
            config["fixture_dir"] = str(project / "fixture")
            config["workspace_parent"] = str(workspaces)
            for field in ("command", "version_command"):
                config[field] = [part.replace("{config_dir}", str(project)) for part in config[field]]
            # Keep startup observing while the actual browser is alive, rather
            # than letting this short scenario finish before the signal arrives.
            config.update(oracle={"type": "file", "path": "never-ready.txt"}, startup_timeout_seconds=40)
            scenario = root / "scenario.json"
            scenario.write_text(json.dumps(config), encoding="utf-8")
            pids = root / "owned-pids.json"
            snapshot = root / "process_snapshot.py"
            snapshot.write_bytes(Path(process_snapshot.__file__).read_bytes())
            launcher = root / "interrupt.py"
            launcher.write_text(
                "import os,sys,time,json,threading,signal\nfrom pathlib import Path\n"
                "from process_snapshot import descendants\nfrom watchmode_truth_lab.cli import main\n"
                "def interrupt():\n deadline=time.monotonic()+20\n"
                f" while not list(Path({str(workspaces)!r}).glob('*/.wtl-browser-state.json')) and time.monotonic()<deadline:time.sleep(0.02)\n"
                f" owned=descendants(os.getpid());Path({str(pids)!r}).write_text(json.dumps(owned))\n"
                " signal.raise_signal(signal.SIGINT)\n"
                "if __name__=='__main__':\n threading.Thread(target=interrupt,daemon=True).start()\n sys.exit(main(sys.argv[1:]))\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            environment.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
            started = time.monotonic()
            result = None
            try:
                result = subprocess.run([str(executable), str(launcher), str(scenario)], cwd=root, env=environment,
                                        capture_output=True, text=True, encoding="utf-8", timeout=35)
            finally:
                if result is None and pids.exists():
                    for record in json.loads(pids.read_text()):
                        terminate_observed(record)
                if pids.exists():
                    retained = ROOT / "evidence" / "cancellation"
                    retained.mkdir(parents=True, exist_ok=True)
                    (retained / (uuid.uuid4().hex + ".json")).write_bytes(pids.read_bytes())
            self.assertEqual(result.returncode, 130, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertLess(time.monotonic() - started, 20)
            owned = json.loads(pids.read_text())
            self.assertGreaterEqual(len(owned), 3, "No actual adapter/Vite/browser tree observed")
            deadline = time.monotonic() + 3
            while any(is_alive(record) for record in owned) and time.monotonic() < deadline:
                time.sleep(0.05)
            remaining = [record for record in owned if is_alive(record)]
            self.assertFalse(remaining, f"Observed browser process survived cancellation: {remaining}")
