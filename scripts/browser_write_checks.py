"""Exercise actual browser output across a controlled truncate/write boundary."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from test_cycle import ROOT, redact
from watchmode_truth_lab.runner import run
from watchmode_truth_lab.starter import create_starter

WRITER = r'''
import base64, hashlib, json, os, sys, time
from pathlib import Path
target, encoded, mode = sys.argv[1:]
target = Path(target)
content = base64.b64decode(encoded)
observations = []
def snapshot(phase):
    data = target.read_bytes()
    observations.append({"phase": phase, "time_ns": time.time_ns(),
                         "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
snapshot("before")
empty_seen = False
if mode == "overwrite":
    with target.open("wb") as stream:
        stream.flush()
        snapshot("truncated")
        deadline = time.monotonic() + 0.12
        while time.monotonic() < deadline:
            try:
                state = json.loads((target.parent.parent / ".wtl-browser-state.json").read_text(encoding="utf-8"))
                empty_seen |= state.get("token") == ""
            except (OSError, ValueError):
                pass
            time.sleep(0.005)
        stream.write(content)
        stream.flush()
else:
    staged = target.with_name(target.name + ".controlled-save")
    staged.write_bytes(content)
    os.replace(staged, target)
snapshot("final")
print("WTL_WRITE_BOUNDARY " + json.dumps({"snapshots": observations, "empty_dom_seen": empty_seen}))
'''


class BrowserWriteChecks(unittest.TestCase):
    def test_truncated_write_atomic_save_and_stale_control(self):
        policy = os.environ.get("WTL_WRITE_POLICY", "stable")
        output = ROOT / os.environ["WTL_WRITE_EVIDENCE"]
        self.assertTrue(output.resolve().is_relative_to(ROOT / "evidence"))
        output.mkdir(parents=True, exist_ok=False)
        empty_seen = []
        # subTests retain the independent controls even if one experiment fails.
        cases = [("scenario", "overwrite", 5), ("polling", "overwrite", 5),
                 ("scenario", "atomic_replace", 2), ("disabled", "atomic_replace", 1)]
        with tempfile.TemporaryDirectory(dir=ROOT / "reports") as temporary:
            project = Path(temporary) / "browser"
            create_starter(project, "vite-browser")
            (project / "controlled_writer.py").write_text(WRITER, encoding="utf-8")
            if policy == "raw":
                config_path = project / "fixture/vite.config.mjs"
                config_path.write_text(config_path.read_text(encoding="utf-8").replace(
                    "awaitWriteFinish: { stabilityThreshold: 200, pollInterval: 20 },", ""), encoding="utf-8")
            for name, mode, rounds in cases:
                with self.subTest(watcher=name, mutation=mode):
                    config = json.loads((project / (name + ".json")).read_text(encoding="utf-8"))
                    cli = str(ROOT / "node_modules/vite/bin/vite.js")
                    config["command"][2] = cli
                    config["version_command"][1] = cli
                    config["mutation_command"] = ["{python}", "{config_dir}/controlled_writer.py",
                                                  "{target}", "{content_base64}", "{mode}"]
                    scenario = project / "controlled.json"
                    scenario.write_text(json.dumps(config), encoding="utf-8")
                    report = run(scenario, rounds=rounds, mutation=mode)
                    states = [json.loads(line.removeprefix("WTL_BROWSER_STATE ")) for line in report["logs"]
                              if line.startswith("WTL_BROWSER_STATE ")]
                    boundaries = [json.loads(attempt["mutation_command_result"]["diagnostics"].removeprefix("WTL_WRITE_BOUNDARY "))
                                  for attempt in report["attempts"]]
                    empty = any(state["token"] == "" for state in states) or any(b["empty_dom_seen"] for b in boundaries)
                    if name != "disabled" and mode == "overwrite":
                        empty_seen.append(empty)
                    record = {"policy": policy, "controlled_truncation_seconds": 0.12,
                              "empty_dom_observed": empty, "boundaries": boundaries, "report": report}
                    (output / (name + "-" + mode + ".json")).write_text(redact(json.dumps(record, indent=2)) + "\n", encoding="utf-8")
                    self.assertEqual(report["startup"]["status"], "pass", report)
                    self.assertEqual(len({state["session"] for state in states}), 1, states)
                    self.assertTrue(all(state["retainedState"] == "1" for state in states), states)
                    if name == "disabled":
                        self.assertEqual(report["status"], "stale", report)
                        self.assertEqual([state["token"] for state in states], ["seed"])
                    elif policy != "raw" or mode == "atomic_replace":
                        self.assertEqual(report["status"], "pass", report)
                        self.assertFalse(empty, record)
            if policy == "raw":
                self.assertTrue(any(empty_seen), "Controlled truncation did not reproduce empty DOM; do not infer the boundary")
