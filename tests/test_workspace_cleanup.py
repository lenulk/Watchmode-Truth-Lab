import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from watchmode_truth_lab.runner import _cleanup_workspace


class WorkspaceCleanupTests(unittest.TestCase):
    def test_persistent_sharing_error_is_bounded_and_other_errors_propagate(self):
        busy = PermissionError("controlled sharing violation")
        busy.winerror = 32
        temporary = Mock()
        temporary.cleanup.side_effect = busy
        started = time.monotonic()
        with patch("watchmode_truth_lab.runner.os", SimpleNamespace(name="nt")), self.assertRaises(PermissionError):
            _cleanup_workspace(temporary, timeout=0.05)
        self.assertLess(time.monotonic() - started, 0.5)
        wrong = PermissionError("other controlled permission failure")
        wrong.winerror = 13
        temporary.cleanup.side_effect = wrong
        with patch("watchmode_truth_lab.runner.os", SimpleNamespace(name="nt")), self.assertRaises(PermissionError):
            _cleanup_workspace(temporary, timeout=0.05)

    def test_owned_workspace_cleanup_waits_for_directory_handle_release(self):
        temporary = tempfile.TemporaryDirectory(prefix="cleanup-held-cwd-")
        path = Path(temporary.name)
        code = "import ctypes,os,sys,time\n"
        code += "if os.name=='nt':\n k=ctypes.WinDLL('kernel32',use_last_error=True)\n"
        code += " k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]\n"
        code += " k.CreateFileW.restype=ctypes.c_void_p\n k.CloseHandle.argtypes=[ctypes.c_void_p]\n"
        code += " h=k.CreateFileW(sys.argv[1],0,3,None,3,0x02000000,None)\n assert h not in (None,ctypes.c_void_p(-1).value),ctypes.get_last_error()\n"
        code += "print('ready',flush=True)\ntime.sleep(0.35)\nif os.name=='nt':k.CloseHandle(h)\n"
        holder = subprocess.Popen([sys.executable, "-c", code, str(path)], cwd=path, stdout=subprocess.PIPE,
                                  text=True, encoding="utf-8")
        try:
            self.assertEqual(holder.stdout.readline().strip(), "ready")
            _cleanup_workspace(temporary)
            self.assertFalse(path.exists())
        finally:
            holder.wait(timeout=5)
            holder.stdout.close()
            temporary.cleanup()
