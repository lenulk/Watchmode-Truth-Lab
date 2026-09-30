"""Install a pinned Linux Node/Vite toolchain inside an existing project copy."""

import argparse
import hashlib
import inspect
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_VERSION = "24.18.0"
PNPM_VERSION = "11.19.0"


def extract_archive(archive, destination):
    """Check member and link destinations before extraction on older Python."""
    destination = Path(destination).resolve()
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Archive member escapes runtime directory")
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Archive member escapes runtime directory")
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError("Unsupported runtime archive member type")
            if member.issym() or member.islnk():
                link = Path(member.linkname)
                base = target.parent if member.issym() else destination
                if link.is_absolute() or not (base / link).resolve().is_relative_to(destination):
                    raise ValueError("Archive link escapes runtime directory")
        if "filter" in inspect.signature(source.extractall).parameters:
            source.extractall(destination, members=members, filter="data")
        else:
            # Only official SHA-256-verified Node archives reach this branch.
            source.extractall(destination, members=members)


def runtime_environment():
    manifest = json.loads((ROOT / "reports/linux-runtime.json").read_text())
    env = os.environ.copy()
    env["PATH"] = manifest["runtime_bin"] + os.pathsep + env.get("PATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / "reports/playwright-browsers")
    env["WTL_BROWSER_CHANNEL"] = "chromium"
    return manifest, env


def setup():
    if not sys.platform.startswith("linux") or platform.machine() != "x86_64":
        raise RuntimeError("Toolchain setup requires Linux x86_64")
    cache = ROOT / "reports/linux-runtime"
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
        raise RuntimeError("Node archive checksum did not match official manifest")
    runtime = cache / f"node-v{NODE_VERSION}-linux-x64"
    if not (runtime / "bin/node").is_file():
        extract_archive(archive, cache)
    env = os.environ.copy()
    env["PATH"] = str(runtime / "bin") + os.pathsep + env.get("PATH", "")
    node = runtime / "bin/node"
    tools = cache / "tools"
    pnpm = tools / "node_modules/pnpm/bin/pnpm.cjs"
    if not pnpm.is_file():
        subprocess.run([str(node), str(runtime / "lib/node_modules/npm/bin/npm-cli.js"), "install",
                        "--prefix", str(tools), "--ignore-scripts", "--no-audit", "--no-fund",
                        f"pnpm@{PNPM_VERSION}"], cwd=ROOT, env=env, check=True)
    subprocess.run([str(node), str(pnpm), "install", "--frozen-lockfile", "--ignore-scripts"],
                   cwd=ROOT, env=env, check=True)
    manifest = {"node": str(node), "runtime_bin": str(runtime / "bin"), "pnpm": str(pnpm)}
    (ROOT / "reports/linux-runtime.json").write_text(json.dumps(manifest, indent=2) + "\n")
    provenance = {"node_version": NODE_VERSION, "pnpm_version": PNPM_VERSION,
                  "node_archive_url": base_url + archive_name, "node_archive_sha256": expected,
                  "kernel": platform.release(), "python": platform.python_version(),
                  "installation": "project-local runtime and dependencies; no system Node installation"}
    (ROOT / "evidence/linux-toolchain.json").write_text(json.dumps(provenance, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.setup:
        setup()
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if command:
        manifest, env = runtime_environment()
        command = [manifest["node"] if part == "{node}" else sys.executable if part == "{python}" else part
                   for part in command]
        return subprocess.run(command, cwd=ROOT, env=env).returncode
    if not args.setup:
        parser.error("Use --setup or provide a command after --")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
