"""A deliberately small, dependency-free black-box runner."""

import hashlib
import json
import math
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


class ConfigError(ValueError):
    pass


def _inside(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ConfigError(f"Path must be relative to fixture workspace: {relative}")
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ConfigError(f"Path escapes fixture workspace: {relative}")
    return result


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _filesystem_type(path):
    if os.name == "nt":
        import ctypes

        name = ctypes.create_unicode_buffer(256)
        root = Path(path).anchor
        if ctypes.windll.kernel32.GetVolumeInformationW(root, None, 0, None, None, None, name, len(name)):
            return name.value
    elif sys.platform.startswith("linux"):
        try:
            result = subprocess.run(["stat", "-f", "-c", "%T", str(path)], capture_output=True,
                                    text=True, timeout=2, check=True)
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def _read_output(oracle, workspace):
    if oracle["type"] == "file":
        try:
            return _inside(workspace, oracle["path"]).read_bytes(), None
        except FileNotFoundError:
            return None, "file_not_found"
    if oracle["type"] == "http":
        request = urllib.request.Request(oracle["url"], headers={"Cache-Control": "no-cache"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=0.5) as response:
                return response.read(), None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return None, type(exc).__name__
    raise ConfigError("oracle.type must be 'file' or 'http'")


def _observed_value(data, extractor):
    if data is None or extractor is None:
        return data
    match = extractor.search(data)
    return match.group(1) if match else None


def _wait(expected, oracle, workspace, process, timeout, interval, stable, extractor=None):
    start = time.monotonic()
    deadline = start + timeout
    matched_since = None
    last_data = None
    last_raw_data = None
    last_error = None
    samples = 0
    while True:
        raw_data, error = _read_output(oracle, workspace)
        data = _observed_value(raw_data, extractor)
        samples += 1
        if raw_data is not None:
            last_raw_data = raw_data
        if data is not None:
            last_data = data
        last_error = error or ("extract_regex_no_match" if raw_data is not None and data is None else None)
        now = time.monotonic()
        if data == expected:
            if matched_since is None:
                matched_since = now
            if now - matched_since >= stable:
                return {"status": "pass", "latency_ms": round((matched_since - start) * 1000, 1), "samples": samples,
                        "observed_hash": _hash(data), "observed_bytes": len(data)}
        else:
            matched_since = None
        if process.poll() is not None:
            status = "inconclusive"
            reason = f"process_exited_{process.returncode}"
            break
        if now >= deadline:
            if last_error == "extract_regex_no_match":
                status, reason = "inconclusive", "extraction_failed"
            elif last_data is not None:
                status, reason = "stale", "output_mismatch"
            else:
                status, reason = "timeout", "output_unavailable"
            break
        time.sleep(min(interval, max(0, deadline - now)))
    return {"status": status, "reason": reason, "elapsed_ms": round((time.monotonic() - start) * 1000, 1),
            "samples": samples, "observed_hash": _hash(last_data) if last_data is not None else None,
            "observed_bytes": len(last_data) if last_data is not None else None,
            "raw_output_hash": _hash(last_raw_data) if last_raw_data is not None else None,
            "probe_error": last_error}


def _mutate(target, content, mode, intermediate=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    if mode == "overwrite":
        target.write_bytes(content)
    elif mode == "atomic_replace":
        temporary = target.with_name(target.name + ".wtl-" + uuid.uuid4().hex)
        try:
            temporary.write_bytes(content)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    elif mode == "burst":
        target.write_bytes(intermediate if intermediate is not None else b"intermediate-" + content)
        target.write_bytes(content)
    else:
        raise ConfigError(f"Unknown mutation: {mode}")


def _capture(stream, lines):
    for line in iter(stream.readline, ""):
        lines.append(line.rstrip("\r\n")[:2000])
    stream.close()


def _stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def run(config_path, rounds=1, mutation=None):
    started_at = datetime.now(timezone.utc).isoformat()
    if rounds < 1:
        raise ConfigError("rounds must be at least 1")
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ConfigError("Scenario must be a JSON object")
    for field in ("fixture_dir", "mutation_target"):
        if not isinstance(config.get(field), str) or not config[field]:
            raise ConfigError(f"{field} must be a nonempty string")
    if not isinstance(config.get("oracle"), dict):
        raise ConfigError("oracle must be an object")
    if not isinstance(config.get("env", {}), dict):
        raise ConfigError("env must be an object")
    config_dir = config_path.parent
    fixture = (config_dir / config["fixture_dir"]).resolve()
    if not fixture.is_dir():
        raise ConfigError(f"Fixture directory does not exist: {fixture}")
    command = config["command"]
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ConfigError("command must be a nonempty array of strings")
    mode = mutation or config.get("mutation", "overwrite")
    if mode not in {"overwrite", "atomic_replace", "burst"}:
        raise ConfigError(f"Unknown mutation: {mode}")
    oracle = config["oracle"]
    if oracle.get("type") not in {"file", "http"}:
        raise ConfigError("oracle.type must be 'file' or 'http'")
    if oracle["type"] == "file" and (not isinstance(oracle.get("path"), str) or not oracle["path"]):
        raise ConfigError("oracle.path must be a nonempty relative path")
    if oracle["type"] == "http" and (not isinstance(oracle.get("url"), str) or
                                     not oracle["url"].startswith(("http://", "https://"))):
        raise ConfigError("oracle.url must be HTTP or HTTPS")
    extractor = None
    if "extract_regex" in oracle:
        if not isinstance(oracle["extract_regex"], str):
            raise ConfigError("oracle.extract_regex must be a string")
        try:
            extractor = re.compile(oracle["extract_regex"].encode("utf-8"))
        except re.error as exc:
            raise ConfigError(f"Invalid oracle.extract_regex: {exc}") from exc
        if extractor.groups != 1:
            raise ConfigError("oracle.extract_regex must contain exactly one capture group")
    source_template = config.get("mutation_template")
    if source_template is not None and (not isinstance(source_template, str) or source_template.count("{token}") != 1):
        raise ConfigError("mutation_template must be a string with exactly one {token} placeholder")
    if source_template is not None and not isinstance(config.get("initial_expected"), str):
        raise ConfigError("initial_expected is required when mutation_template is set")
    try:
        timeout = float(config.get("timeout_seconds", 5))
        interval = float(config.get("probe_interval_seconds", 0.05))
        stable = float(config.get("stable_seconds", 0.15))
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout, probe interval, and stable duration must be numbers") from exc
    if not all(math.isfinite(value) for value in (timeout, interval, stable)) or timeout <= 0 or interval <= 0 or stable < 0:
        raise ConfigError("timeout and probe interval must be positive; stable duration cannot be negative")

    with tempfile.TemporaryDirectory(prefix="watchmode-truth-lab-") as temporary:
        workspace = Path(temporary).resolve()
        shutil.copytree(fixture, workspace, dirs_exist_ok=True)
        target = _inside(workspace, config["mutation_target"])
        if not target.is_file():
            raise ConfigError("mutation_target must be an existing fixture file")
        if oracle["type"] == "file":
            _inside(workspace, oracle["path"])
        baseline = config["initial_expected"].encode("utf-8") if source_template is not None else target.read_bytes()
        with socket.socket() as probe_socket:
            probe_socket.bind(("127.0.0.1", 0))
            port = probe_socket.getsockname()[1]
        node = shutil.which("node")
        substitutions = {"{workspace}": str(workspace), "{config_dir}": str(config_dir),
                         "{python}": sys.executable, "{port}": str(port)}
        if node:
            substitutions["{node}"] = node
        argv = command[:]
        for key, value in substitutions.items():
            argv = [part.replace(key, value) for part in argv]
        if any("{node}" in part for part in argv):
            raise ConfigError("Node.js was not found on PATH")
        runtime_oracle = dict(oracle)
        for key, value in substitutions.items():
            if "url" in runtime_oracle:
                runtime_oracle["url"] = runtime_oracle["url"].replace(key, value)
        child_env = os.environ.copy()
        for key, value in config.get("env", {}).items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ConfigError("env must map strings to strings")
            for placeholder, replacement in substitutions.items():
                value = value.replace(placeholder, replacement)
            child_env[key] = value
        version = None
        version_command = config.get("version_command")
        if version_command is not None:
            if not isinstance(version_command, list) or not version_command or not all(isinstance(x, str) for x in version_command):
                raise ConfigError("version_command must be a nonempty array of strings")
            version_argv = version_command[:]
            for key, value in substitutions.items():
                version_argv = [part.replace(key, value) for part in version_argv]
            try:
                version_result = subprocess.run(version_argv, cwd=workspace, env=child_env, capture_output=True,
                                                text=True, encoding="utf-8", errors="replace", timeout=5, check=True)
                version = version_result.stdout.strip() or version_result.stderr.strip()
            except (OSError, subprocess.SubprocessError) as exc:
                version = f"unavailable: {type(exc).__name__}"
        logs = deque(maxlen=200)
        kwargs = {"cwd": workspace, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
                  "text": True, "encoding": "utf-8", "errors": "replace", "env": child_env}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        process = subprocess.Popen(argv, **kwargs)
        threads = [threading.Thread(target=_capture, args=(stream, logs), daemon=True) for stream in (process.stdout, process.stderr)]
        for thread in threads:
            thread.start()
        try:
            ready = _wait(baseline, runtime_oracle, workspace, process, timeout, interval, stable, extractor)
            attempts = []
            if ready["status"] == "pass":
                for index in range(rounds):
                    content = f"wtl-{index:04x}-{uuid.uuid4().hex}".encode("ascii")
                    written = source_template.replace("{token}", content.decode("ascii")).encode("utf-8") if source_template else content
                    intermediate = (source_template.replace("{token}", "intermediate-" + content.decode("ascii")).encode("utf-8")
                                    if source_template else None)
                    _mutate(target, written, mode, intermediate)
                    outcome = _wait(content, runtime_oracle, workspace, process, timeout, interval, stable, extractor)
                    attempts.append({"round": index + 1, "mutation": mode, "expected_hash": _hash(content),
                                     "expected_bytes": len(content), **outcome})
                    if outcome["status"] == "inconclusive":
                        break
            status = ("inconclusive" if ready["status"] != "pass" else
                      "inconclusive" if any(a["status"] == "inconclusive" for a in attempts) else
                      "stale" if any(a["status"] == "stale" for a in attempts) else
                      "timeout" if any(a["status"] == "timeout" for a in attempts) else "pass")
            latencies = sorted(a["latency_ms"] for a in attempts if a["status"] == "pass")
            latency_summary = ({"median_ms": median(latencies), "p95_ms": latencies[max(0, (95 * len(latencies) + 99) // 100 - 1)]}
                               if latencies else None)
            report = {"schema_version": 1, "started_at_utc": started_at, "status": status,
                    "config": config_path.name, "config_sha256": _hash(config_path.read_bytes()),
                    "command": command, "tool_version": version,
                    "environment": {"system": platform.system(), "release": platform.release(),
                                    "python": platform.python_version(), "platform": platform.platform(),
                                    "workspace_device": workspace.anchor,
                                    "filesystem_type": _filesystem_type(workspace)},
                    "oracle": runtime_oracle, "startup": ready, "attempts": attempts,
                    "failure_rate": round(sum(a["status"] != "pass" for a in attempts) / len(attempts), 4) if attempts else None,
                    "pass_latency": latency_summary,
                    "logs": [], "reproduction": {"config": config_path.name, "rounds": rounds, "mutation": mode,
                                                  "cli": f"python -m watchmode_truth_lab {config_path.name} --rounds {rounds} --mutation {mode}"}}
        finally:
            _stop(process)
            for thread in threads:
                thread.join(timeout=1)
        report["logs"] = list(logs)
        return report
