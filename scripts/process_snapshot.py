"""Identity-aware process observations for acceptance controllers, not the product."""
import ctypes
import os
import signal
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


def _windows_rows():
    """Native snapshot; exclude generations born after capture began."""
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetSystemTimePreciseAsFileTime.argtypes = [ctypes.POINTER(wintypes.FILETIME)]
    kernel.GetSystemTimePreciseAsFileTime.restype = None
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    stamp = wintypes.FILETIME()
    kernel.GetSystemTimePreciseAsFileTime(ctypes.byref(stamp))
    cutoff = (stamp.dwHighDateTime << 32) | stamp.dwLowDateTime
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    pairs = []
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        present = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while present:
            pairs.append((int(entry.th32ProcessID), int(entry.th32ParentProcessID)))
            present = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(snapshot)
    rows = []
    for pid, parent in pairs:
        if pid == 0:
            continue
        try:
            current = identity(pid)
        except PermissionError:
            # Global protected processes are outside the queryable observation
            # scope. Errors when checking an observed owned record still fail.
            continue
        if current is not None and current["created"] <= cutoff:
            rows.append(dict(current, parent_pid=parent))
    return rows


def descendants(parent):
    if os.name == "nt":
        root = identity(parent)
        if root is None:
            raise RuntimeError("The snapshot root exited")
        rows = _windows_rows()
        recorded_root = next((row for row in rows if row["pid"] == parent), None)
        if recorded_root is None or recorded_root["created"] != root["created"]:
            raise RuntimeError("Snapshot root creation identity changed")
        return select_descendants(parent, rows)
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
