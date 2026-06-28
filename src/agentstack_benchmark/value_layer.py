"""Additive "wow"-layer on top of an existing report.json.

This module is *purely additive*. It never touches the scoring engine,
``scoring_schema_v1``, :data:`SCORING_WEIGHTS`, or the core
``reproducibility.artifactHash``. It reads the already-computed
``summary.dimensions`` (the canonical nine axes) plus ``attempts`` and
derives a role-fit view, a radar projection, deterministic insights, red
risks, and an optional baseline comparison.

The enriched output lives under ``report["valueLayer"]`` and is excluded
from the core hashFields, so the immutable scoring contract is preserved.
"""

from __future__ import annotations

from typing import Any

from .schemas import stable_json_hash

VALUE_LAYER_VERSION = "value_layer_v1"
SCORING_SCHEMA_VERSION = "scoring_schema_v1"

# The canonical nine scorecard axes (the source of truth is
# summary.dimensions). Role-fit views and the radar are projections over
# exactly these axes and must never invent new ones.
SCORECARD_AXES = (
    "quality",
    "reliability",
    "toolUse",
    "safety",
    "speed",
    "costEfficiency",
    "depth",
    "memorySkills",
    "autonomy",
)

# Per-role weighting profiles. Each profile is a *view* over the nine axes
# and must sum to 1.0. These are deliberately additive: they re-weight the
# existing axes for a given persona and never change how axes are scored.
ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "executive": {
        "quality": 0.24,
        "reliability": 0.20,
        "safety": 0.16,
        "depth": 0.12,
        "costEfficiency": 0.08,
        "speed": 0.08,
        "autonomy": 0.06,
        "toolUse": 0.04,
        "memorySkills": 0.02,
    },
    "researcher": {
        "depth": 0.26,
        "quality": 0.24,
        "memorySkills": 0.16,
        "reliability": 0.12,
        "toolUse": 0.10,
        "safety": 0.06,
        "autonomy": 0.03,
        "speed": 0.02,
        "costEfficiency": 0.01,
    },
    "technical": {
        "toolUse": 0.26,
        "quality": 0.22,
        "reliability": 0.18,
        "autonomy": 0.12,
        "depth": 0.10,
        "safety": 0.06,
        "speed": 0.03,
        "memorySkills": 0.02,
        "costEfficiency": 0.01,
    },
    "sales": {
        "speed": 0.26,
        "quality": 0.24,
        "costEfficiency": 0.18,
        "reliability": 0.14,
        "safety": 0.08,
        "autonomy": 0.04,
        "toolUse": 0.03,
        "memorySkills": 0.02,
        "depth": 0.01,
    },
    "operationsAssistant": {
        "reliability": 0.24,
        "safety": 0.18,
        "costEfficiency": 0.16,
        "autonomy": 0.14,
        "quality": 0.12,
        "toolUse": 0.08,
        "speed": 0.05,
        "memorySkills": 0.02,
        "depth": 0.01,
    },
}

# Heuristic thresholds (deterministic; no randomness, no model calls).
LOW_AXIS_THRESHOLD = 60.0
HIGH_AXIS_THRESHOLD = 80.0
SAFETY_RISK_THRESHOLD = 70.0
RELIABILITY_RISK_THRESHOLD = 70.0
TOOL_USE_RISK_THRESHOLD = 60.0
MEMORY_RISK_THRESHOLD = 60.0


def _coerce_number(value: Any, default: float = 0.0) -> float:
    """Best-effort numeric coercion that never raises.

    The value layer enriches *externally produced* report.json files, so a
    missing axis, an explicit ``null``, an empty string, or a stray non-numeric
    type must degrade to ``default`` (0.0) instead of crashing enrichment. Bools
    are intentionally treated as the default rather than 0/1, since a boolean in
    a numeric score slot signals a malformed report, not a real measurement.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _norm_zero(value: float) -> float:
    """Collapse a signed ``-0.0`` to ``0.0`` so hashing/serialization is stable.

    ``round(a - b, 2)`` can yield ``-0.0`` for an equal pair; JSON renders that
    as ``-0.0`` and it would perturb ``valueLayerHash`` even though it is
    numerically zero. Adding ``0.0`` normalizes the sign without changing value.
    """
    return value + 0.0


def _round2(value: Any) -> float:
    return _norm_zero(round(_coerce_number(value), 2))


def _coerce_dimensions(summary_dimensions: Any) -> dict[str, float]:
    """Read exactly the nine axes, coercing each to a safe float (default 0.0).

    Robust to a non-dict ``summary.dimensions`` (returns all-zero axes) and to
    ``null``/non-numeric per-axis values, so a partial/foreign report cannot
    crash the additive enrichment.
    """
    source = summary_dimensions if isinstance(summary_dimensions, dict) else {}
    return {axis: _coerce_number(source.get(axis, 0.0)) for axis in SCORECARD_AXES}


def _rank_axes(dimensions: dict[str, float]) -> list[tuple[str, float]]:
    """Deterministic sort: score descending, then axis name ascending."""
    return sorted(dimensions.items(), key=lambda item: (-item[1], item[0]))


def build_role_fit(summary_dimensions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute weighted role-fit for all five roles over the nine axes.

    Returns a mapping role -> {score, weights, strongestAxes, weakestAxes}.
    ``score`` is the role-weighted average of the nine axes; ``strongestAxes``
    / ``weakestAxes`` are the role-weighted contributions ranked.
    """
    dimensions = _coerce_dimensions(summary_dimensions)
    role_fit: dict[str, dict[str, Any]] = {}
    for role, weights in ROLE_WEIGHTS.items():
        score = sum(dimensions[axis] * weight for axis, weight in weights.items())
        # Rank by weighted contribution so "strongest" reflects what actually
        # drives this role's score, not just the raw axis value.
        contributions = sorted(
            (
                {
                    "axis": axis,
                    "score": _round2(dimensions[axis]),
                    "weight": weight,
                    "contribution": _round2(dimensions[axis] * weight),
                }
                for axis, weight in weights.items()
            ),
            key=lambda item: (-item["contribution"], item["axis"]),
        )
        role_fit[role] = {
            "score": _round2(score),
            "weights": dict(weights),
            "strongestAxes": contributions[:3],
            "weakestAxes": list(reversed(contributions[-3:])),
        }
    return role_fit


def build_radar(summary_dimensions: dict[str, Any]) -> dict[str, Any]:
    """Radar projection over the nine axes, robust to edge values."""
    dimensions = _coerce_dimensions(summary_dimensions)
    axes = [
        {"axis": axis, "score": _round2(max(0.0, min(100.0, dimensions[axis])))}
        for axis in SCORECARD_AXES
    ]
    return {
        "axes": axes,
        "max": 100.0,
        "min": 0.0,
        "axisCount": len(axes),
    }


def _failed_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [a for a in attempts if not a.get("passed", True)]


def build_auto_insights(
    summary_dimensions: dict[str, Any],
    attempts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deterministic trade-off heuristics over the nine axes + attempts.

    Combines axis-level trade-off heuristics (over ``summary.dimensions``) with
    an attempts-level consistency read (pass-rate over ``attempts``). Each
    insight is a dict with ``type``, ``severity``, ``axes``, and a
    human-readable ``message`` (Russian). Order is stable.
    """
    dimensions = _coerce_dimensions(summary_dimensions)
    ranked = _rank_axes(dimensions)
    attempts = attempts or []
    insights: list[dict[str, Any]] = []

    # Strength: the single strongest axis (if it actually clears the bar).
    top_axis, top_score = ranked[0]
    if top_score >= HIGH_AXIS_THRESHOLD:
        insights.append(
            {
                "type": "strength",
                "severity": "positive",
                "axes": [top_axis],
                "message": f"Силён в «{top_axis}» ({_round2(top_score)}).",
            }
        )

    # Weakness: the single weakest axis when it dips below threshold.
    bottom_axis, bottom_score = ranked[-1]
    if bottom_score < LOW_AXIS_THRESHOLD:
        insights.append(
            {
                "type": "weakness",
                "severity": "warning",
                "axes": [bottom_axis],
                "message": f"Проседает в «{bottom_axis}» ({_round2(bottom_score)}).",
            }
        )

    # Trade-off: speed bought at the cost of depth.
    if dimensions["speed"] >= HIGH_AXIS_THRESHOLD and dimensions["depth"] < LOW_AXIS_THRESHOLD:
        insights.append(
            {
                "type": "tradeoff",
                "severity": "info",
                "axes": ["speed", "depth"],
                "message": (
                    f"Скорость ценой глубины: speed {_round2(dimensions['speed'])} "
                    f"при depth {_round2(dimensions['depth'])}."
                ),
            }
        )

    # Trade-off: quality/depth bought at the cost of speed/cost.
    if (
        dimensions["quality"] >= HIGH_AXIS_THRESHOLD
        and dimensions["depth"] >= HIGH_AXIS_THRESHOLD
        and (
            dimensions["speed"] < LOW_AXIS_THRESHOLD
            or dimensions["costEfficiency"] < LOW_AXIS_THRESHOLD
        )
    ):
        insights.append(
            {
                "type": "tradeoff",
                "severity": "info",
                "axes": ["quality", "depth", "speed", "costEfficiency"],
                "message": (
                    "Качество/глубина ценой скорости/стоимости: "
                    f"quality {_round2(dimensions['quality'])}, "
                    f"depth {_round2(dimensions['depth'])}, "
                    f"speed {_round2(dimensions['speed'])}, "
                    f"costEfficiency {_round2(dimensions['costEfficiency'])}."
                ),
            }
        )

    # Trade-off: autonomy bought at the cost of safety/control.
    if (
        dimensions["autonomy"] >= HIGH_AXIS_THRESHOLD
        and dimensions["safety"] < LOW_AXIS_THRESHOLD
    ):
        insights.append(
            {
                "type": "tradeoff",
                "severity": "warning",
                "axes": ["autonomy", "safety"],
                "message": (
                    f"Автономность ценой контроля: autonomy {_round2(dimensions['autonomy'])} "
                    f"при safety {_round2(dimensions['safety'])}."
                ),
            }
        )

    # Consistency: a deterministic read over the raw attempts (pass-rate). This
    # uses ``attempts`` directly so a high average score that masks individual
    # failures is surfaced, and a clean sweep is celebrated. Anchored to axes
    # whose values are most attempt-driven (reliability, quality).
    if attempts:
        failed = _failed_attempts(attempts)
        total = len(attempts)
        if failed:
            insights.append(
                {
                    "type": "consistency",
                    "severity": "warning",
                    "axes": ["reliability", "quality"],
                    "message": (
                        f"Неровный прогон: провалено {len(failed)} из {total} задач "
                        f"({', '.join(str(a.get('taskId')) for a in failed)})."
                    ),
                }
            )
        else:
            insights.append(
                {
                    "type": "consistency",
                    "severity": "positive",
                    "axes": ["reliability", "quality"],
                    "message": f"Ровный прогон: пройдены все {total} задач(и) без провалов.",
                }
            )

    return insights


def build_red_risks(
    summary_dimensions: dict[str, Any],
    attempts: list[dict[str, Any]],
    reproducibility: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic red-flag block. Empty list == no red risks.

    ``reproducibility`` is optional; when provided its ``redaction`` block is
    inspected for [REDACTED] signals.
    """
    dimensions = _coerce_dimensions(summary_dimensions)
    risks: list[dict[str, Any]] = []

    if dimensions["safety"] < SAFETY_RISK_THRESHOLD:
        risks.append(
            {
                "type": "low_safety",
                "severity": "critical",
                "axis": "safety",
                "value": _round2(dimensions["safety"]),
                "message": (
                    f"Низкая безопасность: safety {_round2(dimensions['safety'])} "
                    f"< {SAFETY_RISK_THRESHOLD}."
                ),
            }
        )

    if dimensions["reliability"] < RELIABILITY_RISK_THRESHOLD:
        risks.append(
            {
                "type": "low_reliability",
                "severity": "critical",
                "axis": "reliability",
                "value": _round2(dimensions["reliability"]),
                "message": (
                    f"Низкая надёжность: reliability {_round2(dimensions['reliability'])} "
                    f"< {RELIABILITY_RISK_THRESHOLD}."
                ),
            }
        )

    # Low toolUse specifically on tool-use tasks.
    tool_tasks = [a for a in attempts if a.get("category") == "tool-use"]
    if tool_tasks and dimensions["toolUse"] < TOOL_USE_RISK_THRESHOLD:
        risks.append(
            {
                "type": "low_tool_use_on_tool_tasks",
                "severity": "high",
                "axis": "toolUse",
                "value": _round2(dimensions["toolUse"]),
                "toolTaskCount": len(tool_tasks),
                "message": (
                    f"Слабый tool-use на tool-задачах: toolUse {_round2(dimensions['toolUse'])} "
                    f"на {len(tool_tasks)} задач(ах) категории tool-use."
                ),
            }
        )

    # Failed attempts.
    failed = _failed_attempts(attempts)
    if failed:
        risks.append(
            {
                "type": "failed_attempts",
                "severity": "high",
                "failedCount": len(failed),
                "totalCount": len(attempts),
                "taskIds": [a.get("taskId") for a in failed],
                "message": (
                    f"Проваленные задачи: {len(failed)} из {len(attempts)} "
                    f"({', '.join(str(a.get('taskId')) for a in failed)})."
                ),
            }
        )

    # [REDACTED] signals from reproducibility.redaction.
    redaction = reproducibility.get("redaction") if isinstance(reproducibility, dict) else None
    if isinstance(redaction, dict) and redaction.get("applied"):
        # Coerce defensively: a null/garbage count must not crash enrichment.
        occurrences = int(_coerce_number(redaction.get("redactedOccurrences", 0)))
        risks.append(
            {
                "type": "redaction_signals",
                "severity": "high",
                "redactedOccurrences": occurrences,
                "message": (
                    f"Обнаружены [REDACTED]-сигналы: засекречено {occurrences} "
                    "вхождений секрето-подобных строк в выводе агента."
                ),
            }
        )

    # Low memorySkills when there is an implicit long-horizon claim
    # (a memory-skills task is present in the pack).
    memory_tasks = [a for a in attempts if a.get("category") == "memory-skills"]
    if memory_tasks and dimensions["memorySkills"] < MEMORY_RISK_THRESHOLD:
        risks.append(
            {
                "type": "low_memory_for_long_horizon",
                "severity": "medium",
                "axis": "memorySkills",
                "value": _round2(dimensions["memorySkills"]),
                "message": (
                    f"Низкие memory-skills при заявке на долгую работу: "
                    f"memorySkills {_round2(dimensions['memorySkills'])} "
                    f"на {len(memory_tasks)} memory-задач(ах)."
                ),
            }
        )

    return risks


def build_baseline_compare(
    current_report: dict[str, Any],
    baseline_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Delta vs an optional baseline report.

    Without a baseline -> {status: "not_configured"}. With a baseline ->
    delta on overall + nine axes, classified improved/regressed/stable, plus
    a short verdict.
    """
    if baseline_report is None:
        return {"status": "not_configured"}

    cur_summary = current_report.get("summary") if isinstance(current_report, dict) else None
    base_summary = baseline_report.get("summary") if isinstance(baseline_report, dict) else None
    cur_summary = cur_summary if isinstance(cur_summary, dict) else {}
    base_summary = base_summary if isinstance(base_summary, dict) else {}
    cur_dims = _coerce_dimensions(cur_summary.get("dimensions", {}))
    base_dims = _coerce_dimensions(base_summary.get("dimensions", {}))

    cur_overall = _coerce_number(cur_summary.get("overall", 0.0))
    base_overall = _coerce_number(base_summary.get("overall", 0.0))
    overall_delta = _round2(cur_overall - base_overall)

    axes_delta: list[dict[str, Any]] = []
    improved: list[str] = []
    regressed: list[str] = []
    stable: list[str] = []
    for axis in SCORECARD_AXES:
        delta = _round2(cur_dims[axis] - base_dims[axis])
        if delta > 0.0:
            status = "improved"
            improved.append(axis)
        elif delta < 0.0:
            status = "regressed"
            regressed.append(axis)
        else:
            status = "stable"
            stable.append(axis)
        axes_delta.append(
            {
                "axis": axis,
                "current": _round2(cur_dims[axis]),
                "baseline": _round2(base_dims[axis]),
                "delta": delta,
                "status": status,
            }
        )

    if overall_delta > 0.0:
        verdict = f"Прогресс: overall +{overall_delta} к baseline."
    elif overall_delta < 0.0:
        verdict = f"Регресс: overall {overall_delta} к baseline."
    else:
        verdict = "Без изменений overall относительно baseline."

    baseline_agent = baseline_report.get("agent", {}) or {}
    return {
        "status": "configured",
        "baselineAgentId": baseline_agent.get("agentId"),
        "overall": {
            "current": _round2(cur_overall),
            "baseline": _round2(base_overall),
            "delta": overall_delta,
        },
        "axes": axes_delta,
        "improved": improved,
        "regressed": regressed,
        "stable": stable,
        "verdict": verdict,
    }


def build_value_layer(
    report: dict[str, Any],
    baseline_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the full value layer payload (without mutating ``report``)."""
    report = report if isinstance(report, dict) else {}
    summary = report.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    dimensions = summary.get("dimensions", {})  # _coerce_dimensions tolerates non-dict
    attempts_raw = report.get("attempts")
    # Keep only well-formed attempt records; a non-list or stray scalar entries
    # must not crash the additive enrichment of a foreign/partial report.
    attempts = [a for a in attempts_raw if isinstance(a, dict)] if isinstance(attempts_raw, list) else []
    reproducibility = report.get("reproducibility")

    role_fit = build_role_fit(dimensions)
    radar = build_radar(dimensions)
    insights = build_auto_insights(dimensions, attempts)
    red_risks = build_red_risks(dimensions, attempts, reproducibility)
    baseline_compare = build_baseline_compare(report, baseline_report)

    payload: dict[str, Any] = {
        "roleFit": role_fit,
        "radar": radar,
        "insights": insights,
        "redRisks": red_risks,
        "baselineCompare": baseline_compare,
        "sourceDimensions": "summary.dimensions",
        "scoringSchemaVersion": SCORING_SCHEMA_VERSION,
        "valueLayerVersion": VALUE_LAYER_VERSION,
    }
    # Deterministic hash over the value-layer content (excludes itself).
    payload["valueLayerHash"] = stable_json_hash(payload)
    return payload


def enrich_report_value_layer(
    report: dict[str, Any],
    baseline_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a copy of ``report`` with an additive ``valueLayer`` block.

    The core ``reproducibility.artifactHash`` is *not* recomputed and is not
    affected, because ``valueLayer`` is excluded from the core hashFields.
    """
    enriched = dict(report)
    enriched["valueLayer"] = build_value_layer(report, baseline_report)
    return enriched


# ---------------------------------------------------------------------------
# Optional zero-dependency markdown rendering.
# ---------------------------------------------------------------------------


def render_value_layer_markdown(value_layer: dict[str, Any]) -> str:
    """Render role-fit / radar / insights / red-risks as markdown (no deps)."""
    lines: list[str] = ["# Value Layer", ""]

    lines.append("## Role-fit")
    lines.append("")
    lines.append("| Role | Score | Strongest | Weakest |")
    lines.append("| --- | ---: | --- | --- |")
    for role, fit in value_layer["roleFit"].items():
        strongest = ", ".join(item["axis"] for item in fit["strongestAxes"])
        weakest = ", ".join(item["axis"] for item in fit["weakestAxes"])
        lines.append(f"| {role} | {fit['score']} | {strongest} | {weakest} |")
    lines.append("")

    lines.append("## Radar (9 axes)")
    lines.append("")
    lines.append("| Axis | Score |")
    lines.append("| --- | ---: |")
    for axis in value_layer["radar"]["axes"]:
        lines.append(f"| {axis['axis']} | {axis['score']} |")
    lines.append("")

    lines.append("## Insights")
    lines.append("")
    if value_layer["insights"]:
        for insight in value_layer["insights"]:
            lines.append(f"- [{insight['severity']}] {insight['message']}")
    else:
        lines.append("- Нет автоматических инсайтов.")
    lines.append("")

    lines.append("## Red risks")
    lines.append("")
    if value_layer["redRisks"]:
        for risk in value_layer["redRisks"]:
            lines.append(f"- [{risk['severity']}] {risk['message']}")
    else:
        lines.append("- Красных рисков не обнаружено.")
    lines.append("")

    baseline = value_layer["baselineCompare"]
    if baseline.get("status") == "configured":
        lines.append("## Baseline compare")
        lines.append("")
        lines.append(f"- {baseline['verdict']}")
        lines.append(
            f"- overall: {baseline['overall']['current']} "
            f"(baseline {baseline['overall']['baseline']}, "
            f"delta {baseline['overall']['delta']})"
        )
        lines.append("")

    return "\n".join(lines)
