"""Real installed subprocess cancellation with a controlled in-process SIGINT."""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from test_cleanup import alive
from test_cycle import ROOT


class CancellationChecks(unittest.TestCase):
    def test_installed_sigint_stops_watch_descendants_and_pending_http(self):
        executable = Path(os.environ["WTL_INSTALLED_PYTHON"]).absolute()
        for oracle_type in ("file", "http"):
            with self.subTest(oracle=oracle_type), tempfile.TemporaryDirectory(prefix="cancel-", dir=ROOT / "reports") as temporary:
                root = Path(temporary)
                fixture = root / "fixture"
                fixture.mkdir()
                (fixture / "input.txt").write_bytes(b"seed")
                ready = root / "watch.pid"
                descendant = root / "descendant.pid"
                probe_pids = root / "probe-pids.json"
                worker = root / "watch.py"
                worker.write_text(
                    "import subprocess,sys,time,os,json\nfrom pathlib import Path\n"
                    "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
                    "Path(sys.argv[2]).write_text(str(child.pid))\n"
                    + ("from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer\n"
                       "class Handler(BaseHTTPRequestHandler):\n def do_GET(self):time.sleep(30)\n def log_message(self,*args):pass\n"
                       "server=ThreadingHTTPServer(('127.0.0.1',int(sys.argv[3])),Handler)\n" if oracle_type == "http" else "")
                    + "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                    + ("server.serve_forever()\n" if oracle_type == "http" else "time.sleep(60)\n"), encoding="utf-8")
                config = {"fixture_dir": "fixture", "mutation_target": "input.txt",
                          "command": ["{python}", str(worker), str(ready), str(descendant), "{port}"],
                          "oracle": {"type": "http", "url": "http://127.0.0.1:{port}/"} if oracle_type == "http" else {"type": "file", "path": "output.txt"},
                          "startup_timeout_seconds": 30, "timeout_seconds": 3}
                scenario = root / "scenario.json"
                scenario.write_text(json.dumps(config), encoding="utf-8")
                launcher = root / "interrupt.py"
                launcher.write_text(
                    "import sys,threading,time,signal,multiprocessing,json\nfrom pathlib import Path\n"
                    "from watchmode_truth_lab.cli import main\n"
                    "def interrupt():\n"
                    " deadline=time.monotonic()+10\n"
                    f" while not Path({str(ready)!r}).exists() and time.monotonic()<deadline:time.sleep(0.02)\n"
                    " time.sleep(0.75)\n"
                    f" Path({str(probe_pids)!r}).write_text(json.dumps([p.pid for p in multiprocessing.active_children()]))\n"
                    " signal.raise_signal(signal.SIGINT)\n"
                    "if __name__=='__main__':\n threading.Thread(target=interrupt,daemon=True).start()\n sys.exit(main(sys.argv[1:]))\n", encoding="utf-8")
                environment = os.environ.copy()
                environment.pop("PYTHONPATH", None)
                environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
                started = time.monotonic()
                result = subprocess.run([str(executable), str(launcher), str(scenario)], cwd=root, env=environment,
                                        capture_output=True, text=True, encoding="utf-8", timeout=20)
                self.assertEqual(result.returncode, 130, result.stdout + result.stderr)
                self.assertIn("Cancelled.", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertLess(time.monotonic() - started, 10)
                pids = [int(ready.read_text()), int(descendant.read_text()), *json.loads(probe_pids.read_text())]
                if oracle_type == "http":
                    self.assertGreater(len(pids), 2, "No pending HTTP process existed at interruption")
                deadline = time.monotonic() + 2
                while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertFalse(any(alive(pid) for pid in pids), f"Cancellation leaked processes: {pids}")
