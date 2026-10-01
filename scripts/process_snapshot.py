"""Identity-aware process observations for acceptance controllers, not the product."""
import ctypes
import json
import os
import signal
import subprocess
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def _windows_process(pid, terminate=False):
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000 | 0x100000 | (1 if terminate else 0), False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error in (87, 1168):  # Invalid PID / no longer present.
            yield None
            return
        raise ctypes.WinError(error)
    try:
        state = kernel.WaitForSingleObject(handle, 0)
        if state == 0:
            yield None
            return
        if state != 258:
            raise ctypes.WinError(ctypes.get_last_error())
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
            raise ctypes.WinError(ctypes.get_last_error())
        created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        yield kernel, handle, created
    finally:
        kernel.CloseHandle(handle)


def identity(pid):
    """Return live PID + exact birth identity; query errors are not 'dead'."""
    if os.name == "nt":
        with _windows_process(pid) as process:
            return None if process is None else {"pid": pid, "created": process[2]}
    try:
        data = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    fields = data[data.rfind(")") + 2:].split()
    if fields[0] in ("Z", "X"):
        return None
    return {"pid": pid, "created": int(fields[19]), "parent_pid": int(fields[1])}


def select_descendants(parent, rows):
    """A child cannot precede its current parent; reject recycled-parent links."""
    records = {row["pid"]: row for row in rows}
    if parent not in records:
        raise RuntimeError("The live snapshot root is missing")
    found = {parent}
    while True:
        added = {pid for pid, row in records.items()
                 if row["parent_pid"] in found
                 and row["created"] >= records[row["parent_pid"]]["created"]}
        updated = found | added
        if updated == found:
            return [records[pid] for pid in sorted(found - {parent})]
        found = updated


def descendants(parent):
    if os.name == "nt":
        root = identity(parent)
        if root is None:
            raise RuntimeError("The snapshot root exited")
        command = ("Get-CimInstance Win32_Process | ForEach-Object { if ($_.CreationDate) {"
                   "[pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;"
                   "created=$_.CreationDate.ToUniversalTime().ToFileTimeUtc()} } } | ConvertTo-Json -Compress")
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, text=True, encoding="utf-8", timeout=10, check=True)
        rows = json.loads(result.stdout)
        if isinstance(rows, dict):
            rows = [rows]
        recorded_root = next((row for row in rows if row["pid"] == parent), None)
        # CIM timestamps have microsecond precision; retain exact WinAPI ticks
        # for liveness and termination after matching the same process generation.
        if recorded_root is None or recorded_root["created"] // 10 != root["created"] // 10:
            raise RuntimeError("Snapshot root creation identity changed")
        observed = []
        for row in select_descendants(parent, rows):
            current = identity(row["pid"])
            if current is not None and current["created"] // 10 == row["created"] // 10:
                observed.append(dict(row, created=current["created"]))
        return observed
    rows = []
    for path in Path("/proc").glob("[0-9]*/stat"):
        current = identity(int(path.parent.name))
        if current is not None:
            rows.append(current)
    return select_descendants(parent, rows)


def is_alive(record):
    current = identity(record["pid"])
    return current is not None and current["created"] == record["created"]


def terminate_observed(record):
    """Emergency cleanup uses a stable handle, never kills a reused PID."""
    if os.name == "nt":
        with _windows_process(record["pid"], terminate=True) as process:
            if process is not None and process[2] == record["created"]:
                if not process[0].TerminateProcess(process[1], 1):
                    raise ctypes.WinError(ctypes.get_last_error())
        return
    try:
        descriptor = os.pidfd_open(record["pid"])
    except ProcessLookupError:
        return
    try:
        if is_alive(record):
            signal.pidfd_send_signal(descriptor, signal.SIGTERM)
    finally:
        os.close(descriptor)
