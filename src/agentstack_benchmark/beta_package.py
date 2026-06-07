from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from .schemas import RUN_TRACK_LOCAL_PUBLIC

PUBLIC_BETA_PACKAGE_SCHEMA_VERSION = "agentstack-benchmark.public-beta-package.v0.1"
PACKAGE_STATUS_LOCAL_READY = "local-ready"

REQUIRED_PUBLIC_BETA_ASSETS = [
    "README.md",
    "pyproject.toml",
    "docs/product-technical-spec-v0.1.md",
    "docs/monetization-v0.md",
    "docs/adapter-contract-v0.1.md",
    "docs/scoring-schema-v1.md",
    "docs/reproducibility-redaction.md",
    "docs/local-public-pilots-v0.1.md",
    "docs/hosted-verified-track-v0.1.md",
    "docs/auth-rate-limit-v0.1.md",
    "docs/public-beta-package-v0.1.md",
    "docs/offline-local-mvp-demo.md",
    "docs/local-model-adapter-v0.1.md",
    "docs/first-run-doctor-v0.1.md",
    "examples/manifests/offline_demo.json",
    "examples/task_packs/beta_v0_1.json",
    "examples/pilots/local_public_v0_1.json",
]

LOCAL_VERIFICATION_COMMANDS = [
    "PYTHONPATH=src python3 -m unittest tests.test_beta_package -v",
    "PYTHONPATH=src python3 -m unittest discover -s tests -v",
    "python3 -m compileall -q src examples tests",
    "PYTHONPATH=src python3 -m agentstack_benchmark.cli pilot-run "
    "--out-dir artifacts/runs/pilots-local-public-v0-1",
    "PYTHONPATH=src python3 -m agentstack_benchmark.cli serve "
    "--host 127.0.0.1 --port 8088 --runs-dir artifacts/runs",
    "PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local --once",
    "PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check",
    "PYTHONPATH=src python3 -m agentstack_benchmark.cli doctor",
    "PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local "
    "--agent-mode auto-local-model --once",
]


def build_public_beta_package(repo_root: str | Path, out_dir: str | Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = _build_manifest(repo_root)
    checklist = render_public_beta_checklist(manifest)
    summary = {
        "packageStatus": PACKAGE_STATUS_LOCAL_READY,
        "manifestPath": str(out_dir / "public_beta_manifest.json"),
        "checklistPath": str(out_dir / "PUBLIC_BETA_CHECKLIST.md"),
        "assetCount": len(manifest["assets"]),
        "pricingMode": manifest["pricingMode"],
        "defaultTrack": manifest["defaultTrack"],
    }

    (out_dir / "public_beta_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "PUBLIC_BETA_CHECKLIST.md").write_text(checklist, encoding="utf-8")
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def render_public_beta_checklist(manifest: dict[str, Any]) -> str:
    lines = [
        "# AgentStack Benchmark public beta package",
        "",
        f"Package status: **{PACKAGE_STATUS_LOCAL_READY}**.",
        "",
        "## Included trust foundation",
        "",
        "- Local-public run track with closed enum semantics.",
        "- HTTP adapter contract for local-only preview integrations.",
        "- Frozen deterministic scoring schema v1.",
        "- Reproducibility hash, variance/confidence metadata, and output redaction.",
        "- Five local-public pilot fixtures and a track-aware leaderboard path.",
        "- Offline local MVP demo path for UX testing without internet or API keys.",
        "- Optional local model adapter with loopback autodetect and deterministic fallback.",
        "- First-run doctor command with exact local commands, URLs, and port readiness.",
        "- Hosted-verified boundary scaffold with hidden-task rejection in local runs.",
        "- Optional bearer-auth and rate-limit scaffold for guarded preview serving.",
        "",
        "## Launch boundary",
        "",
        "- No external deploy has been performed.",
        "- No public launch or announcement has been performed.",
        "- No billing/payment flow is included.",
        "- No production credential material is included.",
        "- No hosted runner or hidden task corpus is included.",
        "",
        "## Local verification commands",
        "",
    ]
    for command in manifest["verificationCommands"]:
        lines.append(f"- `{command}`")
    lines.extend(
        [
            "",
            "## Required release assets",
            "",
        ]
    )
    for asset in manifest["assets"]:
        lines.append(f"- `{asset['path']}` — sha256 `{asset['sha256']}`")
    lines.append("")
    return "\n".join(lines)


def _build_manifest(repo_root: Path) -> dict[str, Any]:
    return {
        "schemaVersion": PUBLIC_BETA_PACKAGE_SCHEMA_VERSION,
        "packageName": "agentstack-benchmark-public-beta-local",
        "packageStatus": PACKAGE_STATUS_LOCAL_READY,
        "projectVersion": _read_project_version(repo_root),
        "pricingMode": "free-beta",
        "defaultTrack": RUN_TRACK_LOCAL_PUBLIC,
        "hostedVerifiedStatus": "reserved-server-side-only",
        "deploymentStatus": "local-artifact-not-deployed",
        "billingStatus": "deferred-no-payment-flow",
        "launchActionsPerformed": False,
        "verificationCommands": LOCAL_VERIFICATION_COMMANDS,
        "assets": [
            _asset_entry(repo_root, relative_path)
            for relative_path in REQUIRED_PUBLIC_BETA_ASSETS
        ],
    }


def _read_project_version(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    with pyproject_path.open("rb") as handle:
        pyproject = tomllib.load(handle)
    return str(pyproject.get("project", {}).get("version", "0.0.0"))


def _asset_entry(repo_root: Path, relative_path: str) -> dict[str, Any]:
    asset_path = repo_root / relative_path
    if not asset_path.exists():
        raise FileNotFoundError(f"Required public beta asset is missing: {relative_path}")
    return {
        "path": relative_path,
        "sha256": _sha256_file(asset_path),
        "bytes": asset_path.stat().st_size,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
