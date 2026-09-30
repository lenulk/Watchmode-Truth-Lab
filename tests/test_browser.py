import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from watchmode_truth_lab.runner import run

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe"


def browser_states(report):
    return [json.loads(line.removeprefix("WTL_BROWSER_STATE ")) for line in report["logs"]
            if line.startswith("WTL_BROWSER_STATE ")]


@unittest.skipUnless(((os.name == "nt" and CHROME.exists()) or
                      (sys.platform.startswith("linux") and os.environ.get("WTL_TEST_BROWSER") == "1")) and shutil.which("node") and
                     (ROOT / "node_modules/playwright-core/package.json").exists(),
                     "Requires installed Windows Chrome or Linux browser opt-in, plus pinned Playwright dependency")
class BrowserTests(unittest.TestCase):
    def test_browser_hmr_updates_dom_without_reload(self):
        report = run(ROOT / "vite.browser.json", rounds=2, mutation="atomic_replace")
        self.assertEqual(report["status"], "pass", report)
        states = browser_states(report)
        self.assertGreaterEqual(len(states), 3, report)
        self.assertEqual(len({state["session"] for state in states}), 1, states)
        self.assertGreaterEqual(states[-1]["updates"], 2, states)

    def test_disabled_watcher_keeps_browser_dom_stale(self):
        config = json.loads((ROOT / "vite.browser.json").read_text())
        config["fixture_dir"] = str(ROOT / config["fixture_dir"])
        config["command"] = [value.replace("{config_dir}", str(ROOT)) for value in config["command"]]
        config["version_command"] = [value.replace("{config_dir}", str(ROOT)) for value in config["version_command"]]
        config["env"] = {"WTL_DISABLE_WATCH": "1"}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "browser-disabled.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            report = run(path)
        self.assertEqual(report["startup"]["status"], "pass", report)
        self.assertEqual(report["status"], "stale", report)
        states = browser_states(report)
        self.assertEqual([state["token"] for state in states], ["seed"], states)
        self.assertEqual(states[0]["updates"], 0, states)
