"""Report export and optional human-readable presentation."""

import os
import tempfile
from pathlib import Path


def _write_content(stream, content):
    stream.write(content)
    stream.flush()
    os.fsync(stream.fileno())


def write_report(destination, encoded):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=".wtl-report-", suffix=".tmp", dir=destination.parent)
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            _write_content(stream, encoded + "\n")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def summarize(result):
    lines = ["Watchmode Truth Lab: " + result["status"].upper()]
    if result["status"] == "created":
        lines += [f"Starter: {result['template']}", f"Directory: {result['directory']}", "Read README.md in that directory for the next commands."]
    elif "checks" in result:
        lines += [f"{row['status'].upper()} {row['name']}: {row['message']}" for row in result["checks"]]
    elif "attempts" in result:
        attempts = result["attempts"]
        passed = sum(row["status"] == "pass" for row in attempts)
        lines.append(f"Rounds: {passed}/{len(attempts)} passed")
        startup = result.get("startup", {})
        if startup.get("status") != "pass":
            lines.append("Startup: " + startup.get("reason", startup.get("status", "unknown")))
        for row in attempts:
            if row["status"] != "pass":
                lines.append(f"Round {row['round']}: {row['status']} ({row.get('reason', 'unknown')})")
        if result.get("pass_latency"):
            lines.append(f"Observed latency: median {result['pass_latency']['median_ms']} ms; p95 {result['pass_latency']['p95_ms']} ms")
        if result["status"] != "pass":
            lines.append("Inspect startup, per-round reason and logs in the JSON report; a deadline is scenario policy.")
    else:
        lines.append("Scenario: " + result.get("config", "unknown"))
    return "\n".join(lines)
