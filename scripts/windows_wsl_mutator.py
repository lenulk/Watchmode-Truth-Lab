"""Invoke an actual Windows process to mutate a Linux fixture via WSL UNC."""

import shutil
import subprocess
import sys
from pathlib import Path


def windows_path(path):
    return subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()


def main():
    workspace, target, mode, content, intermediate = sys.argv[1:]
    root = Path(workspace).resolve()
    source = Path(target).resolve()
    if not source.is_relative_to(root):
        raise RuntimeError("Target escapes fixture workspace")
    powershell = shutil.which("powershell.exe")
    if not powershell:
        powershell = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    command = [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
               windows_path(Path(__file__).with_name("windows_mutation.ps1")),
               "-WorkspacePath", windows_path(root), "-TargetPath", windows_path(source),
               "-Mode", mode, "-ContentBase64", content, "-IntermediateBase64", intermediate,
               "-AccessMode", "MountedWindows" if str(root).startswith("/mnt/") else "UNC"]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
