from __future__ import annotations

from typing import Any

from .schemas import RUN_TRACK_HOSTED_VERIFIED, RUN_TRACK_LOCAL_PUBLIC, validate_run_track

TRACK_CAPABILITIES_SCHEMA_VERSION = "agentstack-benchmark.track-capabilities.v0.1"
PUBLIC_TASK_VISIBILITY = "public"
HIDDEN_TASK_VISIBILITY = "hidden"


def build_track_capabilities() -> dict[str, Any]:
    return {
        "schemaVersion": TRACK_CAPABILITIES_SCHEMA_VERSION,
        "defaultTrack": RUN_TRACK_LOCAL_PUBLIC,
        "tracks": [
            {
                "track": RUN_TRACK_LOCAL_PUBLIC,
                "status": "active",
                "assignmentAuthority": "local-runner",
                "localRunnerCanAssign": True,
                "hiddenTasksAllowed": False,
                "taskVisibility": [PUBLIC_TASK_VISIBILITY],
                "requiresHostedInfra": False,
                "description": (
                    "Open/local benchmark track. Public task packs are runnable locally; "
                    "reports are reproducible but not server-verified."
                ),
            },
            {
                "track": RUN_TRACK_HOSTED_VERIFIED,
                "status": "reserved",
                "assignmentAuthority": "server-side-hosted-runner",
                "localRunnerCanAssign": False,
                "hiddenTasksAllowed": True,
                "taskVisibility": [PUBLIC_TASK_VISIBILITY, HIDDEN_TASK_VISIBILITY],
                "requiresHostedInfra": True,
                "description": (
                    "Reserved hosted track for server-side verified runs. Hidden tasks "
                    "belong only to this track and are not shipped in local task packs."
                ),
            },
        ],
        "localRunnerPolicy": {
            "assignedTrack": RUN_TRACK_LOCAL_PUBLIC,
            "rejectsHiddenTasks": True,
            "canAssignHostedVerified": False,
            "hiddenTaskError": "hidden tasks require hosted-verified server-side runner",
        },
    }


def validate_local_public_task_pack(task_pack: dict[str, Any]) -> None:
    hidden_task_ids = [
        str(task.get("taskId", "<unknown>"))
        for task in task_pack.get("tasks", [])
        if _is_hidden_task(task)
    ]
    if hidden_task_ids:
        joined = ", ".join(hidden_task_ids)
        raise ValueError(
            "hidden tasks require hosted-verified server-side runner; "
            f"local-public runner rejected: {joined}"
        )


def _is_hidden_task(task: dict[str, Any]) -> bool:
    visibility = str(task.get("visibility", PUBLIC_TASK_VISIBILITY))
    if visibility not in {PUBLIC_TASK_VISIBILITY, HIDDEN_TASK_VISIBILITY}:
        raise ValueError("task visibility must be one of: public, hidden")
    required_track = task.get("requiresTrack")
    if required_track is not None:
        required_track = validate_run_track(str(required_track))
    return (
        bool(task.get("hidden", False))
        or visibility == HIDDEN_TASK_VISIBILITY
        or required_track == RUN_TRACK_HOSTED_VERIFIED
    )
