"""Run through test_cycle after Linux browser experiments to inspect cleanup."""

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_processes():
    processes = []
    for directory in Path("/proc").glob("[0-9]*"):
        try:
            executable = (directory / "exe").resolve(strict=True)
            if not executable.is_relative_to(ROOT / "reports"):
                continue
            if executable.name not in {"node", "chrome", "chrome_crashpad_handler"}:
                continue
            stat = (directory / "stat").read_text()
            state = stat[stat.rfind(")") + 2:].split()[0]
            if state != "Z":
                processes.append({"pid": int(directory.name), "executable": executable.name, "state": state})
        except OSError:
            continue
    return processes


@unittest.skipUnless(sys.platform.startswith("linux") and (ROOT / "reports/linux-runtime.json").is_file(),
                     "Requires the project-local Linux runtime; run after browser tests finish")
class LinuxProcessChecks(unittest.TestCase):
    def test_no_project_node_or_chromium_process_remains(self):
        deadline = time.monotonic() + 3
        remaining = project_processes()
        while remaining and time.monotonic() < deadline:
            time.sleep(0.05)
            remaining = project_processes()
        self.assertEqual(remaining, [], "Project-local Node or Chromium survived completed experiments")
