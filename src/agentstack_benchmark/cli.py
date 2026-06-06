from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import run_benchmark


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentstack-benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a benchmark task pack against an agent manifest")
    run_parser.add_argument("--manifest", required=True, help="Path to agent manifest JSON")
    run_parser.add_argument("--task-pack", required=True, help="Path to task pack JSON")
    run_parser.add_argument("--out", required=True, help="Output directory for report.json/report.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        report = run_benchmark(args.manifest, args.task_pack, args.out)
        print(json.dumps({"overall": report["summary"]["overall"], "out": str(Path(args.out))}, ensure_ascii=False))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
