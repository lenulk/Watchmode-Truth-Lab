"""Build wheel/sdist once and retain checksums and package source identity."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Output must be a new directory; previous artifacts are retained")
    (ROOT / "reports").mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    if os.environ.get("WTL_BUILD_BACKEND"):
        environment["PYTHONPATH"] = str(Path(os.environ["WTL_BUILD_BACKEND"]).resolve())
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    with tempfile.TemporaryDirectory(prefix="release-build-", dir=ROOT / "reports") as temporary:
        source = Path(temporary)
        for name in ("pyproject.toml", "LICENSE"):
            shutil.copy2(ROOT / name, source / name)
        shutil.copytree(ROOT / "watchmode_truth_lab", source / "watchmode_truth_lab",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        identity = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(source.rglob("*")) if path.is_file()}
        result = subprocess.run([sys.executable, "-c",
                                 "import setuptools,setuptools.build_meta;print('BUILD_BACKEND',setuptools.__version__);setuptools.build_meta.build_wheel('dist');setuptools.build_meta.build_sdist('dist')"],
                                cwd=source, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=90)
        if result.returncode:
            print(result.stdout + result.stderr, file=sys.stderr)
            return result.returncode
        artifacts = sorted((source / "dist").iterdir())
        if len(artifacts) != 2:
            raise RuntimeError("Expected exactly one wheel and one sdist")
        output.mkdir(parents=True, exist_ok=False)
        records = []
        for path in artifacts:
            shutil.copy2(path, output / path.name)
            records.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size})
        manifest = {"artifacts": records, "package_source_sha256": identity,
                    "build_backend": next(line for line in result.stdout.splitlines() if line.startswith("BUILD_BACKEND "))}
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (output / "SHA256SUMS").write_text("".join(f"{record['sha256']}  {record['file']}\n" for record in records), encoding="utf-8")
        print(f"Built {len(artifacts)} artifacts with manifest and SHA256SUMS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
