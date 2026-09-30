"""Create runnable starter projects from installed package resources."""

import json
import os
import shutil
import tempfile
from importlib.resources import files
from pathlib import Path

from .runner import ConfigError

TEMPLATES = ("file", "vite-http", "vite-browser")


def _copy_resources(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir():
        if entry.is_dir():
            _copy_resources(entry, destination / entry.name)
        else:
            (destination / entry.name).write_bytes(entry.read_bytes())


def create_starter(destination, template="file"):
    if template not in TEMPLATES:
        raise ConfigError(f"Unknown starter template: {template}")
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ConfigError("Starter destination must be a new directory; existing work is never overwritten")
    if not destination.parent.is_dir():
        raise ConfigError("Starter parent directory must already exist")
    assets = files("watchmode_truth_lab").joinpath("assets")
    staged = Path(tempfile.mkdtemp(prefix=".wtl-starter-", dir=destination.parent))
    try:
        config = {"fixture_dir": "fixture", "mutation_target": "input.txt",
                  "command": ["{python}", "{config_dir}/worker.py", "{workspace}/input.txt", "{workspace}/output.txt"],
                  "oracle": {"type": "file", "path": "output.txt"},
                  "startup_timeout_seconds": 5, "timeout_seconds": 3,
                  "probe_interval_seconds": 0.03, "stable_seconds": 0.1}
        setup = "No extra dependency is required for the file starter."
        if template == "file":
            _copy_resources(assets.joinpath("file"), staged)
            (staged / "fixture").mkdir()
            (staged / "fixture/input.txt").write_text("seed", encoding="utf-8")
        else:
            _copy_resources(assets.joinpath("common"), staged)
            _copy_resources(assets.joinpath("vite"), staged)
            config.update(mutation_target="src/token.js", mutation_template='export const token = "{token}";\n',
                          initial_expected="seed", startup_timeout_seconds=15, timeout_seconds=8)
            cli = "{config_dir}/node_modules/vite/bin/vite.js"
            config["version_command"] = ["{node}", cli, "--version"]
            config["command"] = ["{node}", cli, "{workspace}", "--host", "127.0.0.1", "--port", "{port}", "--strictPort"]
            config["oracle"] = {"type": "http", "url": "http://127.0.0.1:{port}/src/token.js",
                                "extract_regex": r'export const token = "([^"]+)"'}
            setup = "Install Node.js and pnpm, then run `pnpm install --frozen-lockfile` in this directory."
            if template == "vite-browser":
                config["command"] = ["{node}", "{config_dir}/browser_probe.mjs", cli, "{workspace}", "{port}", "{workspace}/.wtl-browser-state.json"]
                config["oracle"] = {"type": "file", "path": ".wtl-browser-state.json", "extract_regex": r'"token":"([^"]+)"'}
                config["env"] = {"WTL_DOM_SELECTOR": "#build-token", "WTL_STATE_SELECTOR": "#count", "WTL_CLICK_SELECTOR": "#increment"}
                setup += "\nInstall a browser with `pnpm exec playwright-core install chromium` (Linux also needs its system libraries), then set `WTL_BROWSER_CHANNEL=chromium`. Alternatively use installed Chrome or Edge (`WTL_BROWSER_CHANNEL=msedge`)."
        for filename, environment in (("scenario.json", {}), ("polling.json", {"WTL_USE_POLLING": "1"}),
                                      ("disabled.json", {"WTL_DISABLE_WATCH": "1"})):
            if template == "file" and filename != "scenario.json":
                continue
            environment = {**config.get("env", {}), **environment}
            (staged / filename).write_text(json.dumps({**config, **({"env": environment} if environment else {})}, indent=2) + "\n", encoding="utf-8")
        guide = f"# Watchmode Truth Lab: {template}\n\n{setup}\n\n" \
                "From this directory:\n\n```sh\nwatchmode-truth-lab scenario.json --validate\n" \
                "watchmode-truth-lab scenario.json --doctor\n" \
                "watchmode-truth-lab scenario.json --rounds 20 --mutation atomic_replace --report reports/result.json\n```\n\n" \
                "The runner mutates an isolated fixture copy. JSON output is the default; add `--format summary` for a short explanation. " \
                "For Vite, polling.json exercises polling and disabled.json is an expected-stale control (exit 1). " \
                "Browser results describe this dependency-accept fixture; adapt its DOM/session contract to your application. " \
                "Only use commands/configurations you trust; this tool is not an executable sandbox.\n"
        (staged / "README.md").write_text(guide, encoding="utf-8")
        # mkdir is exclusive on both platforms, protecting a destination created
        # by someone else during staging. Only move into a directory we created.
        destination.mkdir()
        try:
            for entry in staged.iterdir():
                os.replace(entry, destination / entry.name)
        except BaseException:
            shutil.rmtree(destination)
            raise
    finally:
        shutil.rmtree(staged)
    return {"status": "created", "template": template, "directory": str(destination), "scenario": "scenario.json"}
