import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path

from watchmode_truth_lab.runner import ConfigError, run


ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def test_example_passes_all_mutation_modes(self):
        for mode in ("overwrite", "atomic_replace", "burst"):
            with self.subTest(mode=mode):
                result = run(ROOT / "example.json", rounds=2, mutation=mode)
                self.assertEqual(result["status"], "pass", result)
                self.assertEqual(len(result["attempts"]), 2)
                self.assertTrue(all(a["expected_hash"] == a["observed_hash"] for a in result["attempts"]))

    def test_stale_output_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "input.txt").write_bytes(b"seed")
            worker = root / "once.py"
            worker.write_text("import pathlib,sys,time\npathlib.Path(sys.argv[2]).write_bytes(pathlib.Path(sys.argv[1]).read_bytes())\ntime.sleep(10)\n", encoding="utf-8")
            config = {"fixture_dir": "fixture", "command": ["{python}", str(worker), "{workspace}/input.txt", "{workspace}/output.txt"],
                      "mutation_target": "input.txt", "oracle": {"type": "file", "path": "output.txt"},
                      "timeout_seconds": 0.35, "probe_interval_seconds": 0.02, "stable_seconds": 0.02}
            path = root / "scenario.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            result = run(path)
            self.assertEqual(result["status"], "stale", result)
            self.assertEqual(result["attempts"][0]["reason"], "output_mismatch")

    def test_http_oracle_checks_response_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "input.txt").write_bytes(b"seed")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            worker = root / "http_worker.py"
            worker.write_text(
                "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
                "from pathlib import Path\nimport sys\n"
                "source=Path(sys.argv[1])\n"
                "class Handler(BaseHTTPRequestHandler):\n"
                " def do_GET(self):\n"
                "  body=source.read_bytes()\n"
                "  self.send_response(200)\n"
                "  self.send_header('Content-Length', str(len(body)))\n"
                "  self.end_headers()\n"
                "  self.wfile.write(body)\n"
                " def log_message(self, *args): pass\n"
                "HTTPServer(('127.0.0.1', int(sys.argv[2])), Handler).serve_forever()\n",
                encoding="utf-8",
            )
            config = {"fixture_dir": "fixture", "command": ["{python}", str(worker), "{workspace}/input.txt", str(port)],
                      "mutation_target": "input.txt", "oracle": {"type": "http", "url": f"http://127.0.0.1:{port}/"},
                      "timeout_seconds": 2, "probe_interval_seconds": 0.02, "stable_seconds": 0.05}
            path = root / "scenario.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            result = run(path)
            self.assertEqual(result["status"], "pass", result)

    def test_templated_source_and_extracted_file_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "input.js").write_text('export const token = "seed";\n', encoding="utf-8")
            worker = root / "transform.py"
            worker.write_text(
                "from pathlib import Path\nimport sys,time\n"
                "src,dst=map(Path,sys.argv[1:3])\nprevious=None\n"
                "while True:\n"
                " data=src.read_bytes()\n"
                " if data!=previous:\n"
                "  dst.write_bytes(b'// transformed\\n'+data)\n"
                "  previous=data\n"
                " time.sleep(0.02)\n", encoding="utf-8")
            config = {"fixture_dir": "fixture", "command": ["{python}", str(worker), "{workspace}/input.js", "{workspace}/output.js"],
                      "mutation_target": "input.js", "mutation_template": 'export const token = "{token}";\n',
                      "initial_expected": "seed", "oracle": {"type": "file", "path": "output.js",
                      "extract_regex": 'export const token = "([^"]+)"'},
                      "timeout_seconds": 2, "probe_interval_seconds": 0.02, "stable_seconds": 0.05}
            path = root / "scenario.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            result = run(path, rounds=2, mutation="burst")
            self.assertEqual(result["status"], "pass", result)
            self.assertEqual(result["attempts"][1]["expected_hash"], result["attempts"][1]["observed_hash"])

    @unittest.skipUnless(shutil.which("node") and (ROOT / "node_modules" / "vite" / "bin" / "vite.js").exists(),
                         "Pinned Vite dependency is not installed")
    def test_vite_native_module_response(self):
        result = run(ROOT / "vite.native.json", rounds=1)
        self.assertEqual(result["status"], "pass", result)
        self.assertIn("vite/8.3.1", result["tool_version"])
        self.assertEqual(result["config"], "vite.native.json")
        self.assertNotIn(str(ROOT.parent), json.dumps({"config": result["config"],
                                                        "environment": result["environment"],
                                                        "reproduction": result["reproduction"]}))

    def test_rejects_mutation_outside_temporary_workspace(self):
        config = json.loads((ROOT / "example.json").read_text(encoding="utf-8"))
        config["mutation_target"] = "../outside.txt"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scenario.json"
            config["fixture_dir"] = str(ROOT / "examples" / "fixture")
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(ConfigError):
                run(path)

    def test_rejects_nonfinite_timeout(self):
        config = json.loads((ROOT / "example.json").read_text(encoding="utf-8"))
        config["timeout_seconds"] = "NaN"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scenario.json"
            config["fixture_dir"] = str(ROOT / "examples" / "fixture")
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(ConfigError):
                run(path)


if __name__ == "__main__":
    unittest.main()
