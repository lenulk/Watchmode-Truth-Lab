"""Scenario-specific dependency checks without running the watched command."""

import json
import os
import re
import shutil
import sys
from pathlib import Path

from .runner import _run_captured, prepare_scenario


def diagnose(config_path, rounds=1, mutation=None):
    scenario = prepare_scenario(config_path, rounds, mutation)
    root = scenario["config_dir"]
    substitutions = {"{config_dir}": str(root), "{workspace}": str(scenario["fixture"]),
                     "{python}": sys.executable, "{node}": shutil.which("node") or "{node}", "{port}": "0"}
    environment = os.environ.copy()
    for key, value in scenario["config"].get("env", {}).items():
        for name, replacement in substitutions.items():
            value = value.replace(name, replacement)
        environment[key] = value
    checks = []

    def record(name, passed, message):
        checks.append({"name": name, "status": "pass" if passed else "fail", "message": message})

    record("scenario", True, "Configuration and fixture paths are valid; watched commands were not started")
    for field in ("command", "mutation_command", "version_command"):
        argv = scenario["config"].get(field)
        if argv is None:
            continue
        executable = argv[0]
        for name, replacement in substitutions.items():
            executable = executable.replace(name, replacement)
        if not Path(executable).is_absolute() and ("/" in executable or "\\" in executable):
            executable = str(scenario["fixture"] / executable)
        found = shutil.which(executable, path=environment.get("PATH"))
        record(field + ".executable", bool(found), "Executable found" if found else "Executable unavailable; install it or correct command/PATH")
        for index, argument in enumerate(argv[1:], 1):
            if "{config_dir}/" in argument or "{config_dir}\\" in argument:
                candidate = argument.replace("{config_dir}", str(root))
                if not any(token in candidate for token in ("{workspace}", "{port}")):
                    record(f"{field}.asset.{index}", Path(candidate).exists(),
                           "Referenced asset found" if Path(candidate).exists() else "Referenced asset missing; install dependencies or correct its path")
    manifest = root / "package.json"
    packages_ready = True
    if manifest.is_file() and any("node_modules" in part for part in scenario["command"]):
        package = json.loads(manifest.read_text(encoding="utf-8"))
        dependencies = package.get("devDependencies", {}) if isinstance(package, dict) else None
        if not isinstance(dependencies, dict):
            packages_ready = False
            record("manifest", False, "package.json and devDependencies must be JSON objects; correct the manifest")
            dependencies = {}
        for name, expected in dependencies.items():
            if not re.fullmatch(r"(?:@[A-Za-z0-9_.-]+/)?[A-Za-z0-9_-][A-Za-z0-9_.-]*", name) or not isinstance(expected, str) or not expected.strip():
                packages_ready = False
                record("manifest.dependency", False, "Dependency names and version specifications must be valid nonempty strings; correct the manifest")
                continue
            target = root / "node_modules" / name / "package.json"
            try:
                installed = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else None
            except (OSError, ValueError):
                installed = None
            actual = installed.get("version") if isinstance(installed, dict) else None
            exact = bool(re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", expected))
            passed = isinstance(actual, str) and bool(actual) and (actual == expected if exact else True)
            packages_ready &= passed
            message = f"Installed {actual}" + ("; range compatibility not verified" if not exact else "")
            record("dependency." + name, passed, message if passed else "Dependency metadata missing, invalid or differs from pinned manifest; run pnpm install --frozen-lockfile")
    if any(part.endswith("browser_probe.mjs") for part in scenario["command"]):
        engine = environment.get("WTL_BROWSER_ENGINE", "chromium")
        if engine not in {"chromium", "firefox", "webkit"}:
            record("browser", False, "WTL_BROWSER_ENGINE must be chromium, firefox or webkit")
        elif not packages_ready or not (root / "node_modules/playwright-core/package.json").is_file() or substitutions["{node}"] == "{node}":
            record("browser", False, "Install Node and pinned Playwright dependency before checking browser availability")
        else:
            # This fixed probe launches and closes only a browser, never Vite or
            # scenario commands. It also detects missing Linux shared libraries.
            code = "const {createRequire}=require('node:module');const p=createRequire(process.argv[1])('playwright-core');" \
                   "const e=process.env.WTL_BROWSER_ENGINE||'chromium';" \
                   "(async()=>{let b;try{b=await p[e].launch({headless:true,...(e==='chromium'?{channel:process.env.WTL_BROWSER_CHANNEL||'chrome'}:{})});" \
                   "console.log('Browser available: '+b.version())}finally{await b?.close()}})().catch(e=>{console.error(e.message);process.exitCode=1});"
            try:
                result = _run_captured([substitutions["{node}"], "-e", code, str(manifest)], root, environment, 15)
                record("browser", result["returncode"] == 0, result["diagnostics"].strip() or "Browser probe did not complete")
            except OSError as exc:
                record("browser", False, f"Browser probe could not start: {type(exc).__name__}")
    return {"status": "ready" if all(check["status"] == "pass" for check in checks) else "not_ready",
            "config": scenario["config_path"].name, "checks": checks}
