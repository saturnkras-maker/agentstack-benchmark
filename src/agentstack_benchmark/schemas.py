from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RUN_TRACK_LOCAL_PUBLIC = "local-public"
RUN_TRACK_HOSTED_VERIFIED = "hosted-verified"
ALLOWED_RUN_TRACKS = {RUN_TRACK_LOCAL_PUBLIC, RUN_TRACK_HOSTED_VERIFIED}


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def stable_json_hash(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_run_track(track: str) -> str:
    if track not in ALLOWED_RUN_TRACKS:
        raise ValueError(f"track must be one of: {', '.join(sorted(ALLOWED_RUN_TRACKS))}")
    return track


def canonicalize_report(report: dict[str, Any]) -> dict[str, Any]:
    track = validate_run_track(str(report.get("track", RUN_TRACK_LOCAL_PUBLIC)))
    canonical: dict[str, Any] = {}
    if "schemaVersion" in report:
        canonical["schemaVersion"] = report["schemaVersion"]
    canonical["track"] = track
    for key, value in report.items():
        if key not in {"schemaVersion", "track"}:
            canonical[key] = value
    return canonical


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())
