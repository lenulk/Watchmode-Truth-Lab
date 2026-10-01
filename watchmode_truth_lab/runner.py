"""A deliberately small, dependency-free black-box runner."""

import hashlib
import base64
import json
import math
import os
import platform
import re
import shutil
import shlex
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from .http_probe import HTTPProbe


class ConfigError(ValueError):
    pass


def _cleanup_workspace(temporary, timeout=2):
    if os.name != "nt":
        temporary.cleanup()
        return

    def onerror(function, path, information):
        error = information[1]
        if isinstance(error, FileNotFoundError):
            return
        # Reset an owned read-only entry once per attempt. Never follow a link
        # or recursively call rmtree from an error handler (Python 3.10 does).
        if isinstance(error, PermissionError) and getattr(error, "winerror", None) == 5 and not Path(path).is_symlink():
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        raise error

    # The context owns explicit cleanup, including failure reporting. Disarm
    # the stdlib finalizer so a persistent lock cannot start its old recursive
    # permission handler after our bounded failure. Required CI checks the
    # supported Python versions' finalizer compatibility.
    temporary._finalizer.detach()
    deadline = time.monotonic() + timeout
    while True:
        try:
            shutil.rmtree(temporary.name, onerror=onerror)
            return
        except PermissionError as exc:
            if os.name != "nt" or getattr(exc, "winerror", None) not in {5, 32} or time.monotonic() >= deadline:
                raise
            # Retry only the owned workspace and the observed Windows boundary.
            time.sleep(min(0.025, max(0, deadline - time.monotonic())))


@contextmanager
def _temporary_workspace(parent):
    temporary = tempfile.TemporaryDirectory(prefix="watchmode-truth-lab-", dir=parent)
    try:
        yield temporary.name
    finally:
        _cleanup_workspace(temporary)


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


def _read_output(oracle, workspace, timeout=0.5, http_probe=None):
    limit = oracle.get("max_output_bytes", 1024 * 1024)
    if oracle["type"] == "file":
        try:
            path = _inside(workspace, oracle["path"])
            if not path.is_file():
                return None, "file_not_found_or_not_regular"
            with path.open("rb") as stream:
                data = stream.read(limit + 1)
            return (None, "body_too_large") if len(data) > limit else (data, None)
        except OSError as exc:
            return None, type(exc).__name__
    if oracle["type"] == "http":
        return http_probe.read(oracle["url"], timeout, limit)
    raise ConfigError("oracle.type must be 'file' or 'http'")


def _observed_value(data, extractor):
    if data is None or extractor is None:
        return data
    match = extractor.search(data)
    return match.group(1) if match else None


def _wait(expected, oracle, workspace, process, timeout, interval, stable, extractor=None, http_probe=None):
    owned_probe = HTTPProbe() if oracle.get("type") == "http" and http_probe is None else None
    try:
        return _wait_observations(expected, oracle, workspace, process, timeout, interval, stable,
                                  extractor, http_probe or owned_probe)
    finally:
        if owned_probe is not None:
            owned_probe.close()
        elif http_probe is not None:
            http_probe.cancel_pending()


def _wait_observations(expected, oracle, workspace, process, timeout, interval, stable, extractor, http_probe):
    start = time.monotonic()
    deadline = start + timeout
    matched_since = None
    last_data = None
    last_raw_data = None
    last_error = None
    samples = 0
    while True:
        remaining = deadline - time.monotonic()
        raw_data, error = _read_output(oracle, workspace, max(0, min(0.5, remaining)), http_probe)
        data = _observed_value(raw_data, extractor)
        samples += 1
        if raw_data is not None:
            last_raw_data = raw_data
        if data is not None:
            last_data = data
        last_error = error or ("extract_regex_no_match" if raw_data is not None and data is None else None)
        now = time.monotonic()
        if process.poll() is not None:
            status = "inconclusive"
            reason = f"process_exited_{process.returncode}"
            break
        if now >= deadline:
            if data == expected or (error == "probe_pending" and last_data == expected):
                status, reason = "timeout", "observation_deadline_exceeded"
            elif last_error in {"extract_regex_no_match", "body_too_large"}:
                status, reason = "inconclusive", last_error
            elif last_data is not None:
                status, reason = "stale", "output_mismatch"
            else:
                status, reason = "timeout", "output_unavailable"
            break
        if data == expected:
            if matched_since is None:
                matched_since = now
            if now - matched_since >= stable:
                return {"status": "pass", "latency_ms": round((matched_since - start) * 1000, 1), "samples": samples,
                        "observed_hash": _hash(data), "observed_bytes": len(data)}
        elif error != "probe_pending":
            matched_since = None
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
    retained = ""
    try:
        for chunk in iter(lambda: stream.readline(2048), ""):
            retained = (retained + chunk)[:2000]
            if chunk.endswith("\n"):
                lines.append(retained.rstrip("\r\n"))
                retained = ""
        if retained:
            lines.append(retained.rstrip("\r\n"))
    finally:
        stream.close()


def _launch(argv, **kwargs):
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        argv = [sys.executable, str(Path(__file__).with_name("process_guard.py")), json.dumps(argv)]
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(argv, **kwargs)


def _external_mutation(command, substitutions, workspace, env, timeout):
    argv = command[:]
    for key, value in substitutions.items():
        argv = [part.replace(key, value) for part in argv]
    result = _run_captured(argv, workspace, env, timeout)
    if result["returncode"] is None:
        result["reason"] = "mutation_deadline_exceeded"
    return result


def _run_captured(argv, workspace, env, timeout):
    started = time.monotonic()
    process = _launch(argv, cwd=workspace, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      text=True, encoding="utf-8", errors="replace")
    lines = deque(maxlen=40)
    threads = [threading.Thread(target=_capture, args=(stream, lines), daemon=True)
               for stream in (process.stdout, process.stderr)]
    for thread in threads:
        thread.start()
    returncode = None
    try:
        deadline = started + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                # Windows waits on a process handle; short slices also return
                # control to Python to deliver pending cancellation signals.
                returncode = process.wait(timeout=min(0.1, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
    finally:
        _stop(process)
        for thread in threads:
            thread.join(timeout=1)
    return {"returncode": returncode, "duration_ms": round((time.monotonic() - started) * 1000, 1),
            "diagnostics": "\n".join(lines)[-2000:]}


def _stop(process):
    if os.name == "nt":
        if process.poll() is None:
            process.kill()  # Guardian job closes and terminates the command tree.
        process.wait(timeout=2)
        return
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
            # The launcher may already have exited while descendants remain.
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def prepare_scenario(config_path, rounds=1, mutation=None):
    """Validate without spawning commands, allocating a workspace, or mutating files."""
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
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
    command = config.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ConfigError("command must be a nonempty array of strings")
    mode = mutation or config.get("mutation", "overwrite")
    if not isinstance(mode, str) or mode not in {"overwrite", "atomic_replace", "burst"}:
        raise ConfigError(f"Unknown mutation: {mode}")
    oracle = config["oracle"]
    if not isinstance(oracle.get("type"), str) or oracle["type"] not in {"file", "http"}:
        raise ConfigError("oracle.type must be 'file' or 'http'")
    limit = oracle.get("max_output_bytes", 1024 * 1024)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 64 * 1024 * 1024:
        raise ConfigError("oracle.max_output_bytes must be an integer between 1 and 67108864")
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
        startup_timeout = float(config.get("startup_timeout_seconds", timeout))
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout, probe interval, and stable duration must be numbers") from exc
    if not all(math.isfinite(value) for value in (timeout, interval, stable, startup_timeout)) or timeout <= 0 or interval <= 0 or stable < 0 or startup_timeout <= 0:
        raise ConfigError("timeout and probe interval must be positive; stable duration cannot be negative")
    if stable >= min(timeout, startup_timeout):
        raise ConfigError("stable duration must be shorter than the observation timeout")
    mutation_command = config.get("mutation_command")
    if mutation_command is not None and (not isinstance(mutation_command, list) or not mutation_command or
                                         not all(isinstance(value, str) for value in mutation_command)):
        raise ConfigError("mutation_command must be a nonempty array of strings")
    try:
        mutation_timeout = float(config.get("mutation_timeout_seconds", 10))
    except (TypeError, ValueError) as exc:
        raise ConfigError("mutation_timeout_seconds must be a positive number") from exc
    if not math.isfinite(mutation_timeout) or mutation_timeout <= 0:
        raise ConfigError("mutation_timeout_seconds must be a positive number")

    temp_parent = config.get("workspace_parent")
    if temp_parent is not None:
        if not isinstance(temp_parent, str):
            raise ConfigError("workspace_parent must be a directory path string")
        temp_parent = (config_dir / temp_parent.replace("{config_dir}", str(config_dir))).resolve()
        if not temp_parent.is_dir():
            raise ConfigError("workspace_parent must be an existing directory")
    target = _inside(fixture, config["mutation_target"])
    if not target.is_file():
        raise ConfigError("mutation_target must be an existing fixture file")
    if oracle["type"] == "file":
        _inside(fixture, oracle["path"])
    for key, value in config.get("env", {}).items():
        if not isinstance(key, str) or not isinstance(value, str) or not key or "=" in key or "\0" in key + value:
            raise ConfigError("env must map valid environment names to strings without NUL")
    for field in ("command", "mutation_command", "version_command"):
        argv = config.get(field)
        if argv is not None and (not isinstance(argv, list) or not argv or
                                 not all(isinstance(value, str) and "\0" not in value for value in argv) or not argv[0]):
            raise ConfigError(f"{field} must be a nonempty argv array without NUL")
    return {"config_path": config_path, "config": config, "config_dir": config_dir, "fixture": fixture,
            "command": command, "mode": mode, "oracle": oracle, "extractor": extractor,
            "source_template": source_template, "timeout": timeout, "interval": interval,
            "stable": stable, "startup_timeout": startup_timeout, "mutation_command": mutation_command,
            "mutation_timeout": mutation_timeout, "temp_parent": temp_parent}


def run(config_path, rounds=1, mutation=None):
    started_at = datetime.now(timezone.utc).isoformat()
    scenario = prepare_scenario(config_path, rounds, mutation)
    config_path = scenario["config_path"]
    config = scenario["config"]
    config_dir = scenario["config_dir"]
    fixture = scenario["fixture"]
    command = scenario["command"]
    mode = scenario["mode"]
    oracle = scenario["oracle"]
    extractor = scenario["extractor"]
    source_template = scenario["source_template"]
    timeout = scenario["timeout"]
    interval = scenario["interval"]
    stable = scenario["stable"]
    startup_timeout = scenario["startup_timeout"]
    mutation_command = scenario["mutation_command"]
    mutation_timeout = scenario["mutation_timeout"]
    temp_parent = scenario["temp_parent"]
    with _temporary_workspace(temp_parent) as temporary:
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
                version_result = _run_captured(version_argv, workspace, child_env, 5)
                version = (version_result["diagnostics"].strip() if version_result["returncode"] == 0 else
                           f"unavailable: command_exit_{version_result['returncode']}")
            except (OSError, subprocess.SubprocessError) as exc:
                version = f"unavailable: {type(exc).__name__}"
        logs = deque(maxlen=200)
        kwargs = {"cwd": workspace, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
                  "text": True, "encoding": "utf-8", "errors": "replace", "env": child_env}
        process = _launch(argv, **kwargs)
        threads = [threading.Thread(target=_capture, args=(stream, logs), daemon=True) for stream in (process.stdout, process.stderr)]
        for thread in threads:
            thread.start()
        http_probe = HTTPProbe() if oracle["type"] == "http" else None
        try:
            ready = _wait(baseline, runtime_oracle, workspace, process, startup_timeout, interval, stable, extractor, http_probe)
            attempts = []
            if ready["status"] == "pass":
                for index in range(rounds):
                    content = f"wtl-{index:04x}-{uuid.uuid4().hex}".encode("ascii")
                    written = source_template.replace("{token}", content.decode("ascii")).encode("utf-8") if source_template else content
                    intermediate = (source_template.replace("{token}", "intermediate-" + content.decode("ascii")).encode("utf-8")
                                    if source_template else None)
                    mutation_info = None
                    if mutation_command is not None:
                        mutation_substitutions = {**substitutions, "{target}": str(target), "{mode}": mode,
                                                  "{content_base64}": base64.b64encode(written).decode("ascii"),
                                                  "{intermediate_base64}": base64.b64encode(intermediate or b"intermediate-" + written).decode("ascii")}
                        mutation_info = _external_mutation(mutation_command, mutation_substitutions, workspace,
                                                           child_env, mutation_timeout)
                    else:
                        _mutate(target, written, mode, intermediate)
                    if mutation_info is not None and mutation_info["returncode"] != 0:
                        outcome = {"status": "inconclusive", "reason": "mutation_command_failed"}
                    else:
                        outcome = _wait(content, runtime_oracle, workspace, process, timeout, interval, stable, extractor, http_probe)
                    attempts.append({"round": index + 1, "mutation": mode, "expected_hash": _hash(content),
                                     "expected_bytes": len(content), "mutation_command_result": mutation_info, **outcome})
                    if outcome["status"] == "inconclusive":
                        break
            status = ("inconclusive" if ready["status"] != "pass" else
                      "inconclusive" if any(a["status"] == "inconclusive" for a in attempts) else
                      "stale" if any(a["status"] == "stale" for a in attempts) else
                      "timeout" if any(a["status"] == "timeout" for a in attempts) else "pass")
            latencies = sorted(a["latency_ms"] for a in attempts if a["status"] == "pass")
            latency_summary = ({"median_ms": median(latencies), "p95_ms": latencies[max(0, (95 * len(latencies) + 99) // 100 - 1)]}
                               if latencies else None)
            reproduction_argv = [sys.executable, "-m", "watchmode_truth_lab", config_path.name,
                                 "--rounds", str(rounds), "--mutation", mode]
            reproduction_cli = ("& " + " ".join("'" + part.replace("'", "''") + "'" for part in reproduction_argv)
                                if os.name == "nt" else shlex.join(reproduction_argv))
            report = {"schema_version": 1, "started_at_utc": started_at, "status": status,
                    "config": config_path.name, "config_sha256": _hash(config_path.read_bytes()),
                    "command": command, "mutation_command": mutation_command, "tool_version": version,
                    "environment": {"system": platform.system(), "release": platform.release(),
                                    "python": platform.python_version(), "platform": platform.platform(),
                                    "workspace_device": workspace.anchor,
                                    "filesystem_type": _filesystem_type(workspace)},
                    "oracle": runtime_oracle, "startup": ready, "attempts": attempts,
                    "failure_rate": round(sum(a["status"] != "pass" for a in attempts) / len(attempts), 4) if attempts else None,
                    "pass_latency": latency_summary,
                    "logs": [], "reproduction": {"config": config_path.name, "rounds": rounds, "mutation": mode,
                                                  "argv": reproduction_argv, "cli_shell": "powershell" if os.name == "nt" else "posix",
                                                  "cli": reproduction_cli}}
        finally:
            if http_probe is not None:
                http_probe.close()
            _stop(process)
            for thread in threads:
                thread.join(timeout=1)
        report["logs"] = list(logs)
        return report
