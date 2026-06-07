from __future__ import annotations

import math
import re
from typing import Any

from .evaluator import SCORING_WEIGHTS
from .schemas import stable_json_hash

REPORT_HASH_FIELDS = [
    "schemaVersion",
    "track",
    "agent",
    "taskPack",
    "scoringSchema",
    "summary",
    "attempts",
]
SECRET_VALUE_PATTERN = re.compile(
    (
        r"(?P<key>\b(?:api[_-]?key|token|secret|password|пароль)\b)"
        r"(?P<sep>\s*[:=]\s*)"
        r"(?P<value>[^\s,;]+)"
    ),
    flags=re.IGNORECASE,
)
REDACTION_REPLACEMENT = "[REDACTED]"


def compute_report_artifact_hash(hash_input: dict[str, Any]) -> str:
    return stable_json_hash(hash_input)


def redact_value(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, list):
        redacted_items = []
        redaction_count = 0
        for item in value:
            redacted_item, item_count = redact_value(item)
            redacted_items.append(redacted_item)
            redaction_count += item_count
        return redacted_items, redaction_count
    if isinstance(value, dict):
        redacted_dict: dict[str, Any] = {}
        redaction_count = 0
        for key, item in value.items():
            redacted_item, item_count = redact_value(item)
            redacted_dict[key] = redacted_item
            redaction_count += item_count
        return redacted_dict, redaction_count
    return value, 0


def build_reproducibility_metadata(
    report: dict[str, Any],
    redacted_occurrences: int,
) -> dict[str, Any]:
    hash_input = {field: report[field] for field in REPORT_HASH_FIELDS}
    return {
        "hashAlgorithm": "sha256",
        "artifactHash": compute_report_artifact_hash(hash_input),
        "hashFields": list(REPORT_HASH_FIELDS),
        "scoreStats": build_score_stats(report["attempts"], report["summary"]),
        "redaction": {
            "applied": redacted_occurrences > 0,
            "replacement": REDACTION_REPLACEMENT,
            "redactedOccurrences": redacted_occurrences,
            "rules": ["secret-like key/value strings"],
        },
    }


def build_score_stats(attempts: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    task_scores = [_attempt_weighted_score(attempt) for attempt in attempts]
    sample_size = len(task_scores)
    if sample_size == 0:
        variance = 0.0
        std_dev = 0.0
        lower = float(summary["overall"])
        upper = float(summary["overall"])
    else:
        mean_score = sum(task_scores) / sample_size
        variance = (
            sum((score - mean_score) ** 2 for score in task_scores) / (sample_size - 1)
            if sample_size > 1
            else 0.0
        )
        std_dev = math.sqrt(variance)
        margin = 1.96 * std_dev / math.sqrt(sample_size)
        lower = max(0.0, float(summary["overall"]) - margin)
        upper = min(100.0, float(summary["overall"]) + margin)
    return {
        "sampleSize": sample_size,
        "taskScoreVariance": round(variance, 4),
        "taskScoreStdDev": round(std_dev, 4),
        "confidenceBand": {
            "confidenceLevel": 0.95,
            "method": "normal_approximation_over_task_weighted_scores",
            "lower": round(lower, 2),
            "upper": round(upper, 2),
        },
    }


def _attempt_weighted_score(attempt: dict[str, Any]) -> float:
    dimensions = dict(attempt["scores"])
    dimensions["reliability"] = 100.0 if attempt["passed"] else 0.0
    return sum(float(dimensions[key]) * weight for key, weight in SCORING_WEIGHTS.items())


def _redact_string(value: str) -> tuple[str, int]:
    redacted, count = SECRET_VALUE_PATTERN.subn(
        lambda match: f"{match.group('key')}{match.group('sep')}{REDACTION_REPLACEMENT}",
        value,
    )
    return redacted, count
