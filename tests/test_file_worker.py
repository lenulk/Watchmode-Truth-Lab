import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'watchmode_truth_lab/assets/file/worker.py'


def deny_read(path):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                                  ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0x80, None)
    if handle in (None, ctypes.c_void_p(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    return lambda: kernel.CloseHandle(handle)


class FileWorkerTests(unittest.TestCase):
    def launch(self, source, output, observed=None):
        argv = [sys.executable, str(WORKER), str(source), str(output)]
        if observed is not None:
            # Observe the real kernel read failure; do not inject an exception.
            code = ("import json,runpy,sys\nfrom pathlib import Path\n"
                    "original=Path.read_bytes;source=Path(sys.argv[2]);marker=Path(sys.argv[4])\n"
                    "def read(path):\n try:return original(path)\n except OSError as error:\n"
                    "  if path==source:marker.write_text(json.dumps({'type':type(error).__name__,'errno':error.errno}),encoding='utf-8')\n"
                    "  raise\nPath.read_bytes=read\nsys.argv=sys.argv[1:4]\nrunpy.run_path(sys.argv[0],run_name='__main__')\n")
            argv = [sys.executable, '-c', code, str(WORKER), str(source), str(output), str(observed)]
        return subprocess.Popen(argv,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8')

    def test_transient_source_read_boundary_recovers(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'reports') as temporary:
            root = Path(temporary)
            source, output = root/'input.txt', root/'output.txt'
            source.write_bytes(b'seed')
            if os.name == 'nt':
                release = deny_read(source)
            else:
                hidden = root/'temporarily-hidden.txt'
                source.rename(hidden)
                release = lambda: hidden.rename(source)
            observed = root/'observed-read-error.json'
            stop_release_wait = threading.Event()
            def release_after_error():
                try:
                    deadline=time.monotonic()+3
                    while not observed.exists() and time.monotonic()<deadline:
                        if stop_release_wait.wait(0.01):
                            break
                    stop_release_wait.wait(0.25)
                finally:
                    release()
            timer=threading.Thread(target=release_after_error)
            timer.start()
            child = None
            try:
                child = self.launch(source, output, observed)
                deadline = time.monotonic() + 3
                while not output.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                diagnostic = child.communicate(timeout=2)[1] if child.poll() is not None else 'No output before bound'
                self.assertTrue(output.exists(), diagnostic)
                self.assertEqual(output.read_bytes(), b'seed')
                self.assertIsNone(child.poll())
                error=json.loads(observed.read_text(encoding='utf-8'))
                self.assertEqual(error['type'],'PermissionError' if os.name=='nt' else 'FileNotFoundError')
            finally:
                stop_release_wait.set()
                timer.join(timeout=4)
                if child is not None:
                    if child.poll() is None:
                        child.kill()
                    child.communicate(timeout=3)
                self.assertFalse(timer.is_alive(), 'Source read handle was not released')

    def test_persistent_read_failure_is_bounded_and_reported(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'reports') as temporary:
            root=Path(temporary);source,output=root/'input.txt',root/'output.txt'
            release = None
            if os.name == 'nt':
                source.write_bytes(b'seed');release=deny_read(source)
            child = self.launch(source,output)
            started=time.monotonic()
            try:
                stdout,stderr=child.communicate(timeout=5)
                self.assertNotEqual(child.returncode,0)
                self.assertIn('PermissionError' if os.name=='nt' else 'FileNotFoundError',stderr)
                self.assertGreater(time.monotonic()-started,0.8)
                self.assertLess(time.monotonic()-started,4)
                self.assertFalse(output.exists())
            finally:
                if child.poll() is None:child.kill()
                child.communicate(timeout=3)
                if release:release()

    def test_unrelated_output_error_propagates(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'reports') as temporary:
            root=Path(temporary);source,output=root/'input.txt',root/'output-directory'
            source.write_bytes(b'seed');output.mkdir()
            child=self.launch(source,output)
            try:
                stdout,stderr=child.communicate(timeout=3)
                self.assertNotEqual(child.returncode,0)
                self.assertIn('write_bytes',stderr)
                self.assertTrue(output.is_dir())
                self.assertEqual(source.read_bytes(),b'seed')
            finally:
                if child.poll() is None:child.kill()
                child.communicate(timeout=3)
