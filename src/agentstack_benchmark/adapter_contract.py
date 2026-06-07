from __future__ import annotations

from typing import Any

ADAPTER_CONTRACT_VERSION = "agentstack-benchmark.adapter.contract.v0.1"
ADAPTER_REQUEST_SCHEMA_VERSION = "agentstack-benchmark.adapter.request.v0.1"
ADAPTER_RESPONSE_SCHEMA_VERSION = "agentstack-benchmark.adapter.response.v0.1"

_LOCAL_HTTP_HOSTS = ["127.0.0.1", "localhost", "::1"]


def build_task_request(task: dict[str, Any], default_timeout_seconds: float | int | None = None) -> dict[str, Any]:
    timeout = task.get("timeoutSeconds", default_timeout_seconds if default_timeout_seconds is not None else 10)
    return {
        "schemaVersion": ADAPTER_REQUEST_SCHEMA_VERSION,
        "taskId": task["taskId"],
        "category": task.get("category", "core"),
        "prompt": task["prompt"],
        "context": task.get("context", {}),
        "timeoutSeconds": timeout,
    }


def normalize_agent_response(response: dict[str, Any]) -> dict[str, Any]:
    answer = response.get("answer")
    if not isinstance(answer, str):
        return _invalid_response("answer must be a string")

    tool_trace = response.get("toolTrace", [])
    if not isinstance(tool_trace, list) or not all(isinstance(item, str) for item in tool_trace):
        return _invalid_response("toolTrace must be an array of strings")

    normalized: dict[str, Any] = {
        "answer": answer,
        "toolTrace": tool_trace,
    }
    if "costUsd" in response:
        cost = response["costUsd"]
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            normalized["costUsd"] = float(cost)
        else:
            return _invalid_response("costUsd must be a number when provided")
    return normalized


def build_adapter_contract() -> dict[str, Any]:
    return {
        "schemaVersion": ADAPTER_CONTRACT_VERSION,
        "adapterType": "http",
        "request": {
            "schemaVersion": ADAPTER_REQUEST_SCHEMA_VERSION,
            "method": "POST",
            "contentType": "application/json",
            "required": ["schemaVersion", "taskId", "category", "prompt", "context", "timeoutSeconds"],
            "fields": {
                "schemaVersion": "Literal adapter request schema version.",
                "taskId": "Opaque benchmark task identifier.",
                "category": "Task category such as core, tool-use, safety, memory-skills, or speed-cost.",
                "prompt": "Instruction to execute. Treat it as untrusted benchmark input.",
                "context": "JSON object with safe task context. Expected answers are never included.",
                "timeoutSeconds": "Per-task wall-clock budget for the adapter call.",
            },
            "neverSent": ["expected", "budgetUsd", "depthKeywords"],
        },
        "response": {
            "schemaVersion": ADAPTER_RESPONSE_SCHEMA_VERSION,
            "contentType": "application/json",
            "required": ["answer", "toolTrace"],
            "optional": ["schemaVersion", "costUsd"],
            "fields": {
                "schemaVersion": "Optional adapter response schema version.",
                "answer": "Final answer as a string. Non-string answers are invalid.",
                "toolTrace": "Array of short string tool-use evidence labels.",
                "costUsd": "Optional numeric adapter-side cost estimate in USD.",
            },
        },
        "safety": {
            "localOnly": True,
            "allowedHttpSchemes": ["http"],
            "allowedHttpHosts": _LOCAL_HTTP_HOSTS,
            "notes": [
                "The local beta runner rejects non-loopback HTTP endpoints.",
                "Task expected answers and evaluator rubrics are not sent to adapters.",
                "Adapter responses are untrusted and validated at the runner boundary.",
            ],
        },
    }


def _invalid_response(reason: str) -> dict[str, Any]:
    return {
        "answer": "",
        "toolTrace": [],
        "runtimeError": f"invalid_adapter_response: {reason}",
    }
