from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import run_benchmark
from .schemas import RUN_TRACK_LOCAL_PUBLIC, validate_run_track

PILOT_REGISTRY_SCHEMA_VERSION = "agentstack-benchmark.pilot-registry.v0.1"
DEFAULT_PILOT_REGISTRY_PATH = Path("examples/pilots/local_public_v0_1.json")


def load_pilot_registry(path: str | Path = DEFAULT_PILOT_REGISTRY_PATH) -> dict[str, Any]:
    registry_path = Path(path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    _validate_pilot_registry(registry)
    return registry


def run_local_pilots(
    registry_path: str | Path = DEFAULT_PILOT_REGISTRY_PATH,
    task_pack_path: str | Path | None = None,
    out_dir: str | Path = "artifacts/runs/pilots-local-public-v0-1",
) -> list[dict[str, Any]]:
    registry_file = Path(registry_path)
    project_root = Path(__file__).resolve().parents[2]
    registry = load_pilot_registry(registry_file)
    task_pack = _resolve_project_path(project_root, task_pack_path or registry["taskPackPath"])
    runs_dir = Path(out_dir)
    results: list[dict[str, Any]] = []

    for pilot in registry["pilots"]:
        manifest_path = _resolve_project_path(project_root, pilot["manifestPath"])
        report_out = runs_dir / pilot["pilotId"]
        report = run_benchmark(manifest_path, task_pack, report_out)
        results.append(
            {
                "pilotId": pilot["pilotId"],
                "agentId": pilot["agentId"],
                "manifestPath": str(manifest_path),
                "outDir": str(report_out),
                "report": report,
            }
        )
    return results


def _resolve_project_path(project_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def _validate_pilot_registry(registry: dict[str, Any]) -> None:
    if registry.get("schemaVersion") != PILOT_REGISTRY_SCHEMA_VERSION:
        raise ValueError(f"schemaVersion must be {PILOT_REGISTRY_SCHEMA_VERSION}")
    if validate_run_track(str(registry.get("track"))) != RUN_TRACK_LOCAL_PUBLIC:
        raise ValueError("pilot registry track must be local-public")
    if registry.get("localOnly") is not True:
        raise ValueError("pilot registry must be localOnly=true")
    pilots = registry.get("pilots")
    if not isinstance(pilots, list) or len(pilots) != 5:
        raise ValueError("pilot registry must contain exactly five pilots")

    seen: set[str] = set()
    for pilot in pilots:
        pilot_id = _require_string(pilot, "pilotId")
        if pilot_id in seen:
            raise ValueError(f"duplicate pilotId: {pilot_id}")
        seen.add(pilot_id)
        if validate_run_track(str(pilot.get("track"))) != RUN_TRACK_LOCAL_PUBLIC:
            raise ValueError(f"pilot {pilot_id} track must be local-public")
        if pilot.get("localPilotMode") != "fixture-adapter":
            raise ValueError(f"pilot {pilot_id} must use fixture-adapter mode")
        if pilot.get("requiresPrivateKeys") is not False:
            raise ValueError(f"pilot {pilot_id} must not require private keys")
        for key in [
            "frameworkName",
            "agentId",
            "manifestPath",
            "selectionRationale",
            "realExecutionBoundary",
        ]:
            _require_string(pilot, key)
        source_urls = pilot.get("sourceUrls")
        if not isinstance(source_urls, list) or not source_urls:
            raise ValueError(f"pilot {pilot_id} must include sourceUrls")
        if not all(isinstance(url, str) and url.startswith("https://") for url in source_urls):
            raise ValueError(f"pilot {pilot_id} sourceUrls must be https URLs")
        coverage = pilot.get("coverage")
        if not isinstance(coverage, list) or len(coverage) < 2:
            raise ValueError(f"pilot {pilot_id} must include at least two coverage tags")


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value
