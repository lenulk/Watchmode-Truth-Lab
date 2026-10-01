"""Real installed subprocess cancellation with a controlled in-process SIGINT."""

import json
import os
import signal
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path

from test_cleanup import alive
from test_cycle import ROOT, redact


class CancellationChecks(unittest.TestCase):
    def test_installed_sigint_stops_watch_descendants_and_pending_http(self):
        executable = Path(os.environ["WTL_INSTALLED_PYTHON"]).absolute()
        for oracle_type in ("file", "http", "mutation"):
            with self.subTest(oracle=oracle_type), tempfile.TemporaryDirectory(prefix="cancel-", dir=ROOT / "reports") as temporary:
                root = Path(temporary)
                fixture = root / "fixture"
                fixture.mkdir()
                (fixture / "input.txt").write_bytes(b"seed")
                ready = root / "watch.pid"
                descendant = root / "descendant.pid"
                probe_pids = root / "probe-pids.json"
                mutator_pid = root / "mutator.pid"
                mutator_child = root / "mutator-child.pid"
                worker = root / "watch.py"
                worker.write_text(
                    "import subprocess,sys,time,os,json\nfrom pathlib import Path\n"
                    "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
                    "Path(sys.argv[2]).write_text(str(child.pid))\n"
                    + ("from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer\n"
                       "class Handler(BaseHTTPRequestHandler):\n def do_GET(self):time.sleep(30)\n def log_message(self,*args):pass\n"
                       "server=ThreadingHTTPServer(('127.0.0.1',int(sys.argv[3])),Handler)\n" if oracle_type == "http" else "")
                    + "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
                    + ("Path('output.txt').write_bytes(b'seed')\n" if oracle_type == "mutation" else "")
                    + ("server.serve_forever()\n" if oracle_type == "http" else "time.sleep(60)\n"), encoding="utf-8")
                config = {"fixture_dir": "fixture", "mutation_target": "input.txt",
                          "command": ["{python}", str(worker), str(ready), str(descendant), "{port}"],
                          "oracle": {"type": "http", "url": "http://127.0.0.1:{port}/"} if oracle_type == "http" else {"type": "file", "path": "output.txt"},
                          "startup_timeout_seconds": 30, "timeout_seconds": 3}
                if oracle_type == "mutation":
                    mutator = root / "mutate.py"
                    mutator.write_text("import os,sys,time,subprocess\nfrom pathlib import Path\n"
                                       "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
                                       "Path(sys.argv[2]).write_text(str(child.pid))\n"
                                       "Path(sys.argv[1]).write_text(str(os.getpid()))\ntime.sleep(30)\n", encoding="utf-8")
                    config.update(mutation_command=["{python}", str(mutator), str(mutator_pid), str(mutator_child)], mutation_timeout_seconds=30)
                scenario = root / "scenario.json"
                scenario.write_text(json.dumps(config), encoding="utf-8")
                launcher = root / "interrupt.py"
                timeline = root / "timeline.jsonl"
                launcher.write_text(
                    "import sys,threading,time,signal,multiprocessing,json,faulthandler\nfrom pathlib import Path\n"
                    "from watchmode_truth_lab.cli import main\n"
                    f"def event(label):\n with Path({str(timeline)!r}).open('a',encoding='utf-8') as target:target.write(json.dumps({{'phase':label,'time':time.monotonic()}})+'\\n')\n"
                    "def interrupt():\n"
                    " deadline=time.monotonic()+10\n"
                    f" while not Path({str(mutator_pid if oracle_type == 'mutation' else ready)!r}).exists() and time.monotonic()<deadline:time.sleep(0.02)\n"
                    " time.sleep(0.75)\n"
                    " event('before_active_children')\n"
                    f" Path({str(probe_pids)!r}).write_text(json.dumps([p.pid for p in multiprocessing.active_children()]))\n"
                    " event('before_raise_signal')\n"
                    " signal.raise_signal(signal.SIGINT)\n"
                    " event('after_raise_signal')\n"
                    "if __name__=='__main__':\n faulthandler.enable()\n faulthandler.dump_traceback_later(5,repeat=True)\n event('main_start')\n threading.Thread(target=interrupt,daemon=True).start()\n result=main(sys.argv[1:])\n event('main_return')\n sys.exit(result)\n", encoding="utf-8")
                environment = os.environ.copy()
                environment.pop("PYTHONPATH", None)
                environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
                started = time.monotonic()
                result = None
                timed_out = None
                try:
                    result = subprocess.run([str(executable), str(launcher), str(scenario)], cwd=root, env=environment,
                                            capture_output=True, text=True, encoding="utf-8", timeout=20)
                except subprocess.TimeoutExpired as error:
                    timed_out = error
                    raise
                finally:
                    def decoded(value):
                        return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value
                    diagnostics = {"oracle": oracle_type, "timed_out": timed_out is not None,
                                   "elapsed_seconds": time.monotonic() - started,
                                   "returncode": None if result is None else result.returncode,
                                   "stdout": decoded(timed_out.stdout) if timed_out else (None if result is None else result.stdout),
                                   "stderr": decoded(timed_out.stderr) if timed_out else (None if result is None else result.stderr),
                                   "timeline": timeline.read_text(encoding='utf-8') if timeline.exists() else None,
                                   "published_pids": {path.name: path.read_text() for path in (ready, descendant, mutator_pid, mutator_child, probe_pids) if path.exists()}}
                    retained = ROOT / "evidence" / "cancellation-diagnostics"
                    retained.mkdir(parents=True, exist_ok=True)
                    (retained / (uuid.uuid4().hex + '-' + oracle_type + '.json')).write_text(redact(json.dumps(diagnostics, indent=2)) + '\n', encoding='utf-8')
                    if result is None:
                        # The controller may have killed only the CLI launcher.
                        # Clean only PIDs published by this test's own workers.
                        for pid_file in (ready, descendant, mutator_pid, mutator_child):
                            if not pid_file.exists():
                                continue
                            pid = int(pid_file.read_text())
                            if os.name == "nt":
                                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=5)
                            else:
                                try:
                                    os.kill(pid, signal.SIGTERM)
                                except ProcessLookupError:
                                    pass
                self.assertEqual(result.returncode, 130, result.stdout + result.stderr)
                self.assertIn("Cancelled.", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertLess(time.monotonic() - started, 10)
                pids = [int(ready.read_text()), int(descendant.read_text()), *json.loads(probe_pids.read_text())]
                if oracle_type == "mutation":
                    pids.extend([int(mutator_pid.read_text()), int(mutator_child.read_text())])
                if oracle_type == "http":
                    self.assertGreater(len(pids), 2, "No pending HTTP process existed at interruption")
                deadline = time.monotonic() + 2
                while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertFalse(any(alive(pid) for pid in pids), f"Cancellation leaked processes: {pids}")
