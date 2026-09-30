import ctypes
import json
import os
import signal
import tempfile
import time
import unittest
from pathlib import Path

from watchmode_truth_lab.runner import run


def alive(pid):
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            return False
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        return stat[stat.rfind(")") + 2:].split()[0] != "Z"
    except FileNotFoundError:
        return False


class CleanupTests(unittest.TestCase):
    def test_child_does_not_survive_exited_launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "input.txt").write_bytes(b"seed")
            pid_file = root / "child.pid"
            launcher = root / "launcher.py"
            launcher.write_text(
                "import pathlib,subprocess,sys\n"
                "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])\n"
                "pathlib.Path(sys.argv[1]).write_text(str(p.pid))\n", encoding="utf-8")
            config = {"fixture_dir": "fixture", "mutation_target": "input.txt",
                      "command": ["{python}", str(launcher), str(pid_file)],
                      "oracle": {"type": "file", "path": "output.txt"},
                      "timeout_seconds": 0.5, "stable_seconds": 0}
            path = root / "scenario.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            pid = None
            try:
                result = run(path)
                self.assertEqual(result["status"], "inconclusive")
                pid = int(pid_file.read_text())
                deadline = time.monotonic() + 0.5
                while alive(pid) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertFalse(alive(pid), "A child survived the scenario cleanup")
            finally:
                if pid is None and pid_file.exists():
                    pid = int(pid_file.read_text())
                if pid is not None and alive(pid):
                    os.kill(pid, signal.SIGTERM)
