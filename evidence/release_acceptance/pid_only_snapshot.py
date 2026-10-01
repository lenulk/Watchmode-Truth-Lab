"""Frozen PID-only function from d7100e3 for historical defect reproduction."""

def descendants(parent):
    import json
    import os
    import subprocess
    from pathlib import Path
    if os.name == "nt":
        command = "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId | ConvertTo-Json -Compress"
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, text=True, encoding="utf-8", timeout=10, check=True)
        rows = json.loads(result.stdout)
        pairs = [(row["ProcessId"], row["ParentProcessId"]) for row in rows]
    else:
        pairs = []
        for path in Path("/proc").glob("[0-9]*/stat"):
            try:
                data = path.read_text()
                pairs.append((int(path.parent.name), int(data[data.rfind(")") + 2:].split()[1])))
            except (OSError, ValueError):
                continue
    found = {parent}
    while True:
        updated = found | {pid for pid, ppid in pairs if ppid in found}
        if updated == found:
            return sorted(found - {parent})
        found = updated
