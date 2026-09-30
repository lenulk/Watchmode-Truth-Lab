import argparse
import json
import sys
from pathlib import Path

from .runner import ConfigError, prepare_scenario, run


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check watch-mode output freshness")
    parser.add_argument("config", type=Path, help="JSON scenario configuration")
    parser.add_argument("--report", type=Path, help="Write JSON report to this path")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--mutation", choices=["overwrite", "atomic_replace", "burst"])
    parser.add_argument("--validate", action="store_true", help="Validate the scenario without starting commands or changing the fixture")
    args = parser.parse_args(argv)
    try:
        if args.validate:
            scenario = prepare_scenario(args.config, rounds=args.rounds, mutation=args.mutation)
            result = {"status": "valid", "config": scenario["config_path"].name,
                      "oracle_type": scenario["oracle"]["type"], "mutation": scenario["mode"]}
        else:
            result = run(args.config, rounds=args.rounds, mutation=args.mutation)
    except (ConfigError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(encoded + "\n", encoding="utf-8")
        except OSError as exc:
            parser.error(f"Cannot write report: {exc}")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(encoded)
    return 0 if result["status"] in {"pass", "valid"} else 1


if __name__ == "__main__":
    sys.exit(main())
