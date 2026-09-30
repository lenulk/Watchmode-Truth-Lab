import argparse
import json
import sys
from pathlib import Path
from . import __version__

from .runner import ConfigError, prepare_scenario, run
from .starter import TEMPLATES, create_starter
from .diagnostics import diagnose
from .reporting import summarize, write_report


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Check watch-mode output freshness")
    parser.add_argument("--version", action="version", version="watchmode-truth-lab " + __version__)
    parser.add_argument("config", type=Path, nargs="?", help="JSON scenario configuration")
    parser.add_argument("--report", type=Path, help="Write JSON report to this path")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--mutation", choices=["overwrite", "atomic_replace", "burst"])
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--validate", action="store_true", help="Validate the scenario without starting commands or changing the fixture")
    actions.add_argument("--init", type=Path, help="Create a starter in a new directory")
    actions.add_argument("--doctor", action="store_true", help="Check scenario dependencies; browser scenarios launch and close a browser probe")
    parser.add_argument("--template", choices=TEMPLATES, default="file")
    parser.add_argument("--format", choices=("json", "summary"), default="json", help="Console output; --report always saves JSON")
    args = parser.parse_args(argv)
    if args.init and args.config:
        parser.error("--init does not accept a scenario path")
    if not args.init and not args.config:
        parser.error("a scenario path or --init is required")
    try:
        if args.init:
            result = create_starter(args.init, args.template)
        elif args.doctor:
            result = diagnose(args.config, rounds=args.rounds, mutation=args.mutation)
        elif args.validate:
            scenario = prepare_scenario(args.config, rounds=args.rounds, mutation=args.mutation)
            result = {"status": "valid", "config": scenario["config_path"].name,
                      "oracle_type": scenario["oracle"]["type"], "mutation": scenario["mode"]}
        else:
            result = run(args.config, rounds=args.rounds, mutation=args.mutation)
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except (ConfigError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        try:
            write_report(args.report, encoded)
        except OSError as exc:
            parser.error(f"Cannot write report: {exc}")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(encoded if args.format == "json" else summarize(result))
    if result["status"] == "not_ready":
        return 2
    return 0 if result["status"] in {"pass", "valid", "created", "ready"} else 1


if __name__ == "__main__":
    sys.exit(main())
