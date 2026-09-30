"""Provision a temporary Linux Vite lab without changing system packages."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE_VERSION = "24.18.0"
PNPM_VERSION = "11.19.0"


def checked(argv, cwd, env):
    subprocess.run(argv, cwd=cwd, env=env, check=True)


def sync_evidence(lab):
    directory = lab / "evidence"
    if directory.exists():
        shutil.copytree(directory, ROOT / "evidence", dirs_exist_ok=True)


def setup():
    if not sys.platform.startswith("linux") or platform.machine() != "x86_64":
        raise RuntimeError("This lab bootstrap requires Linux x86_64")
    cache = Path(tempfile.gettempdir()) / f"watchmode-truth-lab-runtime-{NODE_VERSION}"
    cache.mkdir(parents=True, exist_ok=True)
    archive_name = f"node-v{NODE_VERSION}-linux-x64.tar.xz"
    base_url = f"https://nodejs.org/dist/v{NODE_VERSION}/"
    with urllib.request.urlopen(base_url + "SHASUMS256.txt", timeout=30) as response:
        checksums = response.read().decode("ascii")
    expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1] == archive_name)
    archive = cache / archive_name
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        with urllib.request.urlopen(base_url + archive_name, timeout=30) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Node archive checksum did not match the official manifest")
    runtime = cache / f"node-v{NODE_VERSION}-linux-x64"
    if not (runtime / "bin" / "node").exists():
        with tarfile.open(archive) as source:
            source.extractall(cache, filter="data")
    node = runtime / "bin" / "node"
    env = os.environ.copy()
    env["PATH"] = str(runtime / "bin") + os.pathsep + env.get("PATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    tools = cache / "tools"
    pnpm = tools / "node_modules" / "pnpm" / "bin" / "pnpm.cjs"
    if not pnpm.exists():
        checked([str(node), str(runtime / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js"),
                 "install", "--prefix", str(tools), "--ignore-scripts", "--no-audit", "--no-fund",
                 f"pnpm@{PNPM_VERSION}"], cache, env)
    lab = Path(tempfile.mkdtemp(prefix="watchmode-truth-lab-linux-"))
    shutil.copytree(ROOT, lab, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", "reports", "evidence", "__pycache__"))
    checked([str(node), str(pnpm), "install", "--frozen-lockfile", "--ignore-scripts"], lab, env)
    (ROOT / "reports").mkdir(exist_ok=True)
    local_manifest = {"lab": str(lab), "node": str(node), "runtime_bin": str(runtime / "bin")}
    (ROOT / "reports" / "wsl-lab-local.json").write_text(json.dumps(local_manifest, indent=2), encoding="utf-8")
    provenance = {"node_version": NODE_VERSION, "pnpm_version": PNPM_VERSION,
                  "node_archive_url": base_url + archive_name, "node_archive_sha256": expected,
                  "kernel": platform.release(), "python": platform.python_version(),
                  "installation": "temporary project lab; no system package changes"}
    (ROOT / "evidence" / "wsl2-toolchain.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return lab, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-and-test", action="store_true")
    parser.add_argument("--test-existing", action="store_true")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--windows-mutations", action="store_true")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--mounted-windows", action="store_true")
    args = parser.parse_args()
    if args.setup_and_test:
        lab, env = setup()
        command = [sys.executable, "scripts/test_cycle.py", "--label", "linux-vite-wsl2",
                   "--purpose", "Verify all integrations with Linux Node and Vite inside WSL2"]
    elif args.matrix or args.windows_mutations or args.test_existing:
        manifest = json.loads((ROOT / "reports" / "wsl-lab-local.json").read_text())
        lab = Path(manifest["lab"])
        env = os.environ.copy()
        env["PATH"] = manifest["runtime_bin"] + os.pathsep + env.get("PATH", "")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        shutil.copytree(ROOT, lab, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("node_modules", "reports", "evidence", ".git", "__pycache__"))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if args.test_existing:
            pnpm = Path(manifest["runtime_bin"]).parent.parent / "tools/node_modules/pnpm/bin/pnpm.cjs"
            checked([manifest["node"], str(pnpm), "install", "--frozen-lockfile", "--ignore-scripts"], lab, env)
            command = [sys.executable, "scripts/test_cycle.py", "--label", "final-linux-wsl2",
                       "--purpose", "Verify repaired runner and complete integrations with Linux Node in WSL2"]
        elif args.windows_mutations:
            location = "mounted-ntfs" if args.mounted_windows else "unc"
            command = [sys.executable, "scripts/windows_wsl_cycle.py", "--rounds", str(args.rounds),
                       "--output", f"evidence/matrices/windows-to-wsl2-{location}-{stamp}"]
            if args.mounted_windows:
                parent = ROOT / "reports" / "wsl-mounted-fixtures"
                parent.mkdir(parents=True, exist_ok=True)
                command.extend(["--workspace-parent", str(parent)])
        else:
            command = [sys.executable, "scripts/scenario_cycle.py", "--label", "WSL2 Linux-side edits",
                       "--output", f"evidence/matrices/wsl2-linux-side-{stamp}"]
    else:
        parser.error("Use --setup-and-test, --test-existing, --matrix, or --windows-mutations")
    try:
        result = subprocess.run(command, cwd=lab, env=env)
    finally:
        sync_evidence(lab)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
