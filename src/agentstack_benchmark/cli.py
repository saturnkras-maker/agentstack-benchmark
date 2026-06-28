from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .adapter_contract import build_adapter_contract
from .beta_package import build_public_beta_package
from .leaderboard import build_leaderboard
from .pilots import DEFAULT_PILOT_REGISTRY_PATH, run_local_pilots
from .runner import DEFAULT_HTTP_TIMEOUT_SECONDS, run_benchmark
from .security import SecurityConfig
from .server import serve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentstack-benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Run a benchmark task pack against an agent manifest",
    )
    run_parser.add_argument("--manifest", required=True, help="Path to agent manifest JSON")
    run_parser.add_argument("--task-pack", required=True, help="Path to task pack JSON")
    run_parser.add_argument(
        "--out",
        required=True,
        help="Output directory for report.json/report.md",
    )
    run_parser.add_argument(
        "--http-timeout-seconds",
        type=float,
        default=DEFAULT_HTTP_TIMEOUT_SECONDS,
        help=(
            "Wall-clock timeout (seconds) for the adapter client/transport call "
            "(urllib for http, subprocess for cli). Decoupled from task.timeoutSeconds, "
            "which stays a per-task budget/scoring signal. A manifest "
            "adapter.httpTimeoutSeconds overrides this. Lets real (slow) agents run an "
            "unmodified task pack."
        ),
    )

    leaderboard_parser = subparsers.add_parser(
        "leaderboard",
        help="Build a static leaderboard from run reports",
    )
    leaderboard_parser.add_argument(
        "--runs-dir",
        required=True,
        help="Directory containing run subdirectories",
    )
    leaderboard_parser.add_argument(
        "--out",
        required=True,
        help="Output JSON path; Markdown is written next to it",
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the local free-beta API preview server",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    serve_parser.add_argument("--port", type=int, default=8088, help="TCP port to bind")
    serve_parser.add_argument(
        "--runs-dir",
        default="artifacts/runs",
        help="Directory containing run subdirectories with report.json files",
    )
    serve_parser.add_argument(
        "--api-token-env",
        default=None,
        help="Name of env var containing the optional bearer token; value is never printed",
    )
    serve_parser.add_argument(
        "--rate-limit-requests",
        type=int,
        default=120,
        help="Requests per client per rate-limit window; set 0 to disable",
    )
    serve_parser.add_argument(
        "--rate-limit-window-seconds",
        type=int,
        default=60,
        help="Rate-limit window in seconds",
    )

    pilot_parser = subparsers.add_parser(
        "pilot-run",
        help="Run the local-public five-pilot fixture set",
    )
    pilot_parser.add_argument(
        "--registry",
        default=str(DEFAULT_PILOT_REGISTRY_PATH),
        help="Path to local pilot registry JSON",
    )
    pilot_parser.add_argument(
        "--task-pack",
        default=None,
        help="Override task pack path; defaults to the registry taskPackPath",
    )
    pilot_parser.add_argument(
        "--out-dir",
        default="artifacts/runs/pilots-local-public-v0-1",
        help="Directory where one run subdirectory per pilot is written",
    )
    pilot_parser.add_argument(
        "--leaderboard-out",
        default="artifacts/pilot-leaderboard.json",
        help="Path to write a leaderboard for the generated pilot runs",
    )

    subparsers.add_parser("adapter-contract", help="Print the local HTTP adapter contract as JSON")
    beta_parser = subparsers.add_parser(
        "beta-package",
        help="Write the local public beta package manifest and checklist",
    )
    beta_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root containing README, docs, examples, and pyproject.toml",
    )
    beta_parser.add_argument(
        "--out-dir",
        default="artifacts/public-beta-package",
        help="Directory for public_beta_manifest.json, checklist, and summary.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        report = run_benchmark(
            args.manifest,
            args.task_pack,
            args.out,
            http_timeout_seconds=args.http_timeout_seconds,
        )
        print(
            json.dumps(
                {"overall": report["summary"]["overall"], "out": str(Path(args.out))},
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "leaderboard":
        rows = build_leaderboard(args.runs_dir, args.out)
        print(json.dumps({"entries": len(rows), "out": str(Path(args.out))}, ensure_ascii=False))
        return 0
    if args.command == "serve":
        token = None
        if args.api_token_env:
            token = os.environ.get(args.api_token_env)
            if not token:
                raise SystemExit(f"Missing or empty API token env var: {args.api_token_env}")
        security_config = SecurityConfig.from_token(
            token,
            rate_limit_requests=args.rate_limit_requests,
            rate_limit_window_seconds=args.rate_limit_window_seconds,
        )
        serve(args.host, args.port, args.runs_dir, security_config=security_config)
        return 0
    if args.command == "pilot-run":
        reports = run_local_pilots(args.registry, args.task_pack, args.out_dir)
        rows = build_leaderboard(args.out_dir, args.leaderboard_out)
        print(
            json.dumps(
                {
                    "pilots": len(reports),
                    "leaderboardEntries": len(rows),
                    "outDir": str(Path(args.out_dir)),
                    "leaderboardOut": str(Path(args.leaderboard_out)),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "adapter-contract":
        print(json.dumps(build_adapter_contract(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "beta-package":
        manifest = build_public_beta_package(args.repo_root, args.out_dir)
        print(
            json.dumps(
                {
                    "packageStatus": manifest["packageStatus"],
                    "assetCount": len(manifest["assets"]),
                    "outDir": str(Path(args.out_dir)),
                },
                ensure_ascii=False,
            )
        )
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
