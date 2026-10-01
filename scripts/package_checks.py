"""Build and test an isolated installed wheel through test_cycle --test package_checks."""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
import zipfile
from email.parser import Parser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageChecks(unittest.TestCase):
    def test_wheel_and_installed_console_without_source_checkout(self):
        (ROOT / "reports").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="package-check-", dir=ROOT / "reports") as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            for filename in ("pyproject.toml", "LICENSE"):
                shutil.copy2(ROOT / filename, source / filename)
            shutil.copytree(ROOT / "watchmode_truth_lab", source / "watchmode_truth_lab",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            build_env = os.environ.copy()
            build_env.pop("PYTHONPATH", None)
            if os.environ.get("WTL_BUILD_BACKEND"):
                build_env["PYTHONPATH"] = str(Path(os.environ["WTL_BUILD_BACKEND"]).resolve())
            build_env["PYTHONDONTWRITEBYTECODE"] = "1"
            build_env["PYTHONUTF8"] = "1"
            result = subprocess.run([sys.executable, "-c",
                                     "import setuptools,setuptools.build_meta; print('BUILD_BACKEND',setuptools.__version__); setuptools.build_meta.build_wheel('dist'); setuptools.build_meta.build_sdist('dist')"],
                                    cwd=source, env=build_env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            wheel = next((source / "dist").glob("*.whl"))
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                for filename in ("cli.py", "runner.py", "http_probe.py", "process_guard.py", "__main__.py"):
                    self.assertIn("watchmode_truth_lab/" + filename, names)
                self.assertFalse(any(name.startswith(("evidence/", "reports/", "node_modules/")) for name in names))
                metadata = Parser().parsestr(archive.read(next(name for name in names if name.endswith("/METADATA"))).decode())
                self.assertEqual(metadata["License-Expression"], "MIT")
                self.assertEqual(metadata["Requires-Python"], ">=3.10")
                license_name = next(name for name in names if name.endswith("/licenses/LICENSE"))
                self.assertEqual(archive.read(license_name), (ROOT / "LICENSE").read_bytes())
                for asset in ("assets/file/worker.py", "assets/common/pnpm-lock.yaml", "assets/vite/browser_probe.mjs", "assets/vite/fixture/src/main.js"):
                    self.assertIn("watchmode_truth_lab/" + asset, names)
            unpacked = root / "unpacked"
            unpacked.mkdir()
            with tarfile.open(next((source / "dist").glob("*.tar.gz"))) as archive:
                for member in archive.getmembers():
                    target = (unpacked / member.name).resolve()
                    self.assertTrue(target.is_relative_to(unpacked))
                    self.assertTrue(member.isfile() or member.isdir())
                    if member.isfile():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(archive.extractfile(member).read())
            rebuilt_source = next(unpacked.iterdir())
            rebuilt = subprocess.run([sys.executable, "-c", "import setuptools.build_meta;setuptools.build_meta.build_wheel('rebuilt')"],
                                     cwd=rebuilt_source, env=build_env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(rebuilt.returncode, 0, rebuilt.stdout + rebuilt.stderr)
            rebuilt_wheel = next((rebuilt_source / "rebuilt").glob("*.whl"))
            with zipfile.ZipFile(wheel) as original, zipfile.ZipFile(rebuilt_wheel) as rebuilt:
                for filename in original.namelist():
                    if filename.startswith("watchmode_truth_lab/"):
                        self.assertEqual(original.read(filename), rebuilt.read(filename), filename)
            environment = root / "venv"
            venv.EnvBuilder(with_pip=False).create(environment)
            executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            clean_env = os.environ.copy()
            clean_env.pop("PYTHONPATH", None)
            clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
            clean_env["PYTHONUTF8"] = "1"
            pip_env = clean_env.copy()
            if os.environ.get("WTL_PIP_PATH"):
                pip_env["PYTHONPATH"] = str(Path(os.environ["WTL_PIP_PATH"]).resolve())
            installed = subprocess.run([sys.executable, "-m", "pip", "--python", str(executable), "install",
                                        "--no-index", "--no-deps", "--disable-pip-version-check", str(rebuilt_wheel)],
                                       cwd=root, env=pip_env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            entrypoint = environment / ("Scripts/watchmode-truth-lab.exe" if os.name == "nt" else "bin/watchmode-truth-lab")
            location = subprocess.run([str(executable), "-c", "import watchmode_truth_lab;print(watchmode_truth_lab.__file__)"],
                                      cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(location.returncode, 0, location.stderr)
            self.assertTrue(Path(location.stdout.strip()).is_relative_to(environment))
            version = subprocess.run([str(executable), "-c", "import importlib.metadata,watchmode_truth_lab;assert importlib.metadata.version('watchmode-truth-lab')==watchmode_truth_lab.__version__;print(watchmode_truth_lab.__version__)"],
                                     cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(version.returncode, 0, version.stderr)
            cli_version = subprocess.run([str(entrypoint), "--version"], cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(cli_version.returncode, 0, cli_version.stderr)
            self.assertEqual(cli_version.stdout.strip(), "watchmode-truth-lab " + version.stdout.strip())
            for template in ("file", "vite-http", "vite-browser"):
                starter = root / ("installed-" + template)
                created = subprocess.run([str(entrypoint), "--init", str(starter), "--template", template],
                                         cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=10)
                self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
                validated = subprocess.run([str(entrypoint), str(starter / "scenario.json"), "--validate"],
                                           cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=10)
                self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
                if template == "file":
                    checked = subprocess.run([str(entrypoint), str(starter / "scenario.json"), "--doctor"],
                                             cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=10)
                    self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                    checked = subprocess.run([str(entrypoint), str(starter / "scenario.json"), "--rounds", "2", "--format", "summary"],
                                             cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=15)
                    self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                    self.assertIn("2/2 passed", checked.stdout)
            cases = root / "cases"
            fixture = cases / "fixture"
            fixture.mkdir(parents=True)
            (fixture / "input.txt").write_text("seed")
            shutil.copy2(ROOT / "examples/polling_generator.py", cases / "worker.py")
            config = {"fixture_dir": "fixture", "command": ["{python}", "{config_dir}/worker.py", "{workspace}/input.txt", "{workspace}/output.txt"],
                      "mutation_target": "input.txt", "oracle": {"type": "file", "path": "output.txt"},
                      "startup_timeout_seconds": 5, "timeout_seconds": 3, "stable_seconds": 0.05}
            path = cases / "file scenario's $token ü.json"
            path.write_text(json.dumps(config))
            report = cases / "file-report.json"
            run = subprocess.run([str(entrypoint), str(path), "--rounds", "2", "--mutation", "atomic_replace", "--report", str(report)],
                                 cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "pass")
            self.assertEqual(len(saved["attempts"]), 2)
            self.assertTrue(all(row["expected_hash"] == row["observed_hash"] for row in saved["attempts"]))
            self.assertEqual(saved["reproduction"]["argv"][0], str(executable))
            repeated = subprocess.run(saved["reproduction"]["argv"], cwd=cases, env=clean_env,
                                      capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout)["status"], "pass")
            (cases / "server_worker.py").write_text(
                "from http.server import BaseHTTPRequestHandler,HTTPServer\nfrom pathlib import Path\nimport sys,time\n"
                "class Handler(BaseHTTPRequestHandler):\n"
                " def do_GET(self):\n  time.sleep(0.65)\n  data=Path(sys.argv[1]).read_bytes()\n"
                "  self.send_response(200)\n  self.send_header('Content-Length',str(len(data)))\n  self.end_headers()\n  self.wfile.write(data)\n"
                " def log_message(self,*args):pass\nHTTPServer(('127.0.0.1',int(sys.argv[2])),Handler).serve_forever()\n")
            config["command"] = ["{python}", "{config_dir}/server_worker.py", "{workspace}/input.txt", "{port}"]
            config["oracle"] = {"type": "http", "url": "http://127.0.0.1:{port}/"}
            path = cases / "http.json"
            path.write_text(json.dumps(config))
            run = subprocess.run([str(entrypoint), str(path), "--report", str(cases / "http-report.json")],
                                 cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads((cases / "http-report.json").read_text(encoding="utf-8"))["status"], "pass")
            del config["command"]
            path.write_text(json.dumps(config))
            invalid = subprocess.run([str(entrypoint), str(path)], cwd=root, env=clean_env, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(invalid.returncode, 2, invalid.stderr)
            self.assertNotIn("Traceback", invalid.stderr)
