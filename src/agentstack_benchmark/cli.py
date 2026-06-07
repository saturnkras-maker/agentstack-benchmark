from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .adapter_contract import build_adapter_contract
from .beta_package import build_public_beta_package
from .doctor import build_first_run_doctor_report
from .leaderboard import build_leaderboard
from .local_model import (
    discover_local_model_backend,
    run_local_model_demo_once,
    start_local_model_agent,
)
from .offline_demo import DEFAULT_TASK_PACK_PATH, run_offline_demo_once, start_offline_demo_agent
from .pilots import DEFAULT_PILOT_REGISTRY_PATH, run_local_pilots
from .runner import run_benchmark
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

    demo_parser = subparsers.add_parser(
        "demo-local",
        help="Start the offline local MVP demo agent and UI; no internet or API keys required",
    )
    demo_parser.add_argument("--host", default="127.0.0.1", help="Loopback host to bind")
    demo_parser.add_argument("--agent-port", type=int, default=8765, help="Offline agent port")
    demo_parser.add_argument("--ui-port", type=int, default=8088, help="Preview UI port")
    demo_parser.add_argument(
        "--runs-dir",
        default="artifacts/runs/offline-demo",
        help="Directory where offline demo reports are written",
    )
    demo_parser.add_argument("--run-id", default="offline-demo-run", help="Initial demo run id")
    demo_parser.add_argument(
        "--task-pack",
        default=str(DEFAULT_TASK_PACK_PATH),
        help="Task pack path for the initial demo run",
    )
    demo_parser.add_argument(
        "--once",
        action="store_true",
        help="Run the offline demo benchmark once and exit without serving the UI",
    )
    demo_parser.add_argument(
        "--agent-mode",
        choices=("offline", "auto-local-model", "local-model"),
        default="offline",
        help="Use deterministic offline agent, try a local model with fallback, or require a local model",
    )
    demo_parser.add_argument(
        "--local-model-base-url",
        default=None,
        help="Loopback OpenAI-compatible /v1 or Ollama base URL for local-model modes",
    )
    demo_parser.add_argument(
        "--local-model-name",
        default=None,
        help="Optional local model name override for local-model modes",
    )

    local_model_parser = subparsers.add_parser(
        "local-model-check",
        help="Probe loopback local model backends without internet or API keys",
    )
    local_model_parser.add_argument(
        "--base-url",
        default=None,
        help="Loopback OpenAI-compatible /v1 or Ollama base URL to probe",
    )
    local_model_parser.add_argument(
        "--model",
        default=None,
        help="Optional model name override",
    )

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Print local MVP first-run readiness and exact next commands as JSON",
    )
    doctor_parser.add_argument("--repo-root", default=".", help="Repository root to inspect")
    doctor_parser.add_argument("--host", default="127.0.0.1", help="Loopback host for suggested URLs")
    doctor_parser.add_argument("--ui-port", type=int, default=8088, help="Suggested UI port")
    doctor_parser.add_argument(
        "--agent-port",
        type=int,
        default=8765,
        help="Suggested local agent adapter port",
    )
    doctor_parser.add_argument(
        "--skip-local-model-probe",
        action="store_true",
        help="Skip loopback model probing; useful for instant non-network checks",
    )
    doctor_parser.add_argument(
        "--local-model-base-url",
        default=None,
        help="Optional loopback local model base URL to probe",
    )
    doctor_parser.add_argument(
        "--local-model-name",
        default=None,
        help="Optional local model name override",
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
        report = run_benchmark(args.manifest, args.task_pack, args.out)
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
    if args.command == "demo-local":
        local_backend = None
        fallback_from_local_model = False
        if args.agent_mode in {"auto-local-model", "local-model"}:
            local_backend = discover_local_model_backend(
                base_url=args.local_model_base_url,
                model=args.local_model_name,
                env=dict(os.environ),
            )
        if local_backend and local_backend.available:
            summary = run_local_model_demo_once(
                backend=local_backend,
                runs_dir=args.runs_dir,
                run_id=args.run_id,
                host=args.host,
                agent_port=args.agent_port,
                task_pack_path=args.task_pack,
            )
        else:
            if args.agent_mode == "local-model":
                print(json.dumps({"available": False, "localModelStatus": local_backend.to_dict() if local_backend else None}, ensure_ascii=False))
                return 1
            fallback_from_local_model = args.agent_mode == "auto-local-model"
            summary = run_offline_demo_once(
                runs_dir=args.runs_dir,
                run_id=args.run_id,
                host=args.host,
                agent_port=args.agent_port,
                task_pack_path=args.task_pack,
            )
        base_url = f"http://{args.host}:{args.ui_port}"
        body = {
            **summary,
            "uiUrl": f"{base_url}/",
            "runFormUrl": f"{base_url}/run",
            "reportUrl": f"{base_url}/runs/{args.run_id}",
            "leaderboardUrl": f"{base_url}/leaderboard",
        }
        if fallback_from_local_model:
            body["fallbackFromLocalModel"] = True
            body["localModelStatus"] = local_backend.to_dict() if local_backend else None
        print(json.dumps(body, ensure_ascii=False))
        if args.once:
            return 0
        if local_backend and local_backend.available:
            agent = start_local_model_agent(local_backend, host=args.host, port=args.agent_port)
        else:
            agent = start_offline_demo_agent(host=args.host, port=args.agent_port)
        try:
            serving_body = {
                "status": "serving",
                "agentEndpoint": agent.endpoint,
                "agentMode": body["mode"],
                "uiUrl": body["uiUrl"],
                "runFormUrl": body["runFormUrl"],
                "reportUrl": body["reportUrl"],
                "leaderboardUrl": body["leaderboardUrl"],
            }
            if fallback_from_local_model:
                serving_body["fallbackFromLocalModel"] = True
                serving_body["localModelStatus"] = body.get("localModelStatus")
            print(json.dumps(serving_body, ensure_ascii=False), flush=True)
            security_config = SecurityConfig.from_token(
                None,
                rate_limit_requests=120,
                rate_limit_window_seconds=60,
            )
            serve(args.host, args.ui_port, args.runs_dir, security_config=security_config)
        finally:
            agent.shutdown()
        return 0
    if args.command == "local-model-check":
        backend = discover_local_model_backend(
            base_url=args.base_url,
            model=args.model,
            env=dict(os.environ),
        )
        print(json.dumps(backend.to_dict(), ensure_ascii=False))
        return 0
    if args.command == "doctor":
        report = build_first_run_doctor_report(
            repo_root=args.repo_root,
            host=args.host,
            ui_port=args.ui_port,
            agent_port=args.agent_port,
            probe_local_model=not args.skip_local_model_probe,
            local_model_base_url=args.local_model_base_url,
            local_model_name=args.local_model_name,
            env=dict(os.environ),
        )
        print(json.dumps(report, ensure_ascii=False))
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
