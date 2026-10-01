"""Audit exact distribution bytes against manifest and committed package sources."""

import hashlib
import json
import os
import re
import subprocess
import tarfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_release(directory, revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected an exact Git revision")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    sums = ""
    for record in manifest["artifacts"]:
        path = directory / record["file"]
        if path.name != record["file"] or not path.is_file():
            raise ValueError("Artifact filename or file is invalid")
        content = path.read_bytes()
        if len(content) != record["size_bytes"] or hashlib.sha256(content).hexdigest() != record["sha256"]:
            raise ValueError("Artifact checksum/size differs from immutable manifest")
        sums += record["sha256"] + "  " + record["file"] + "\n"
    if (directory / "SHA256SUMS").read_text(encoding="utf-8") != sums:
        raise ValueError("Published checksum list differs from manifest")
    source_hashes = manifest["package_source_sha256"]
    for name, expected in source_hashes.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or path.parts[0] not in {"watchmode_truth_lab", "pyproject.toml", "LICENSE"}:
            raise ValueError("Package source path is invalid")
        committed = subprocess.run(["git", "-c", f"safe.directory={ROOT}", "show", revision + ":" + name],
                                   cwd=ROOT, capture_output=True, timeout=5, check=True).stdout
        local = (ROOT / path).read_bytes()
        # Git's checkout can convert text line endings. Require exact build
        # identity, and allow only that conversion against committed UTF-8 text.
        committed.decode("utf-8")
        local.decode("utf-8")
        if local.replace(b"\r\n", b"\n") != committed.replace(b"\r\n", b"\n"):
            raise ValueError("Package source differs from verified commit: " + name)
        if expected not in {hashlib.sha256(local).hexdigest(), hashlib.sha256(committed).hexdigest()}:
            raise ValueError("Build source hash differs from checkout/commit: " + name)
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1 or len(manifest["artifacts"]) != 2:
        raise ValueError("Expected one wheel and one source distribution")
    with zipfile.ZipFile(wheels[0]) as wheel:
        for name, expected in source_hashes.items():
            if name.startswith("watchmode_truth_lab/") and hashlib.sha256(wheel.read(name)).hexdigest() != expected:
                raise ValueError("Wheel package payload differs: " + name)
    with tarfile.open(sdists[0]) as source:
        members = {member.name: member for member in source.getmembers()}
        prefix = sdists[0].name.removesuffix(".tar.gz") + "/"
        for name, expected in source_hashes.items():
            member = members[prefix + name]
            if not member.isfile() or hashlib.sha256(source.extractfile(member).read()).hexdigest() != expected:
                raise ValueError("Sdist payload differs: " + name)
    return manifest


class ReleaseArtifactChecks(unittest.TestCase):
    def test_distribution_manifest_sums_and_payload_match_verified_source(self):
        directory = (ROOT / os.environ.get("WTL_RELEASE_DIRECTORY", "reports/ci-release")).resolve()
        revision = os.environ.get("WTL_RELEASE_REVISION") or os.environ["GITHUB_SHA"]
        manifest = verify_release(directory, revision)
        self.assertEqual(len(manifest["artifacts"]), 2)
