from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.cli import main
from agentstack_benchmark.evaluator import SCORING_WEIGHTS
from agentstack_benchmark.reproducibility import (
    REPORT_HASH_FIELDS,
    compute_report_artifact_hash,
)
from agentstack_benchmark.schemas import stable_json_hash
from agentstack_benchmark.value_layer import (
    ROLE_WEIGHTS,
    SCORECARD_AXES,
    build_auto_insights,
    build_baseline_compare,
    build_radar,
    build_red_risks,
    build_role_fit,
    build_value_layer,
    enrich_report_value_layer,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# A "good" agent: high everywhere.
GOOD_DIMENSIONS = {
    "reliability": 100.0,
    "quality": 96.0,
    "speed": 82.0,
    "costEfficiency": 100.0,
    "toolUse": 95.0,
    "safety": 98.0,
    "depth": 88.0,
    "memorySkills": 100.0,
    "autonomy": 100.0,
}

# A "bad" agent: weak safety/reliability/toolUse, failed tasks.
BAD_DIMENSIONS = {
    "reliability": 40.0,
    "quality": 35.0,
    "speed": 90.0,
    "costEfficiency": 100.0,
    "toolUse": 20.0,
    "safety": 30.0,
    "depth": 10.0,
    "memorySkills": 25.0,
    "autonomy": 100.0,
}

GOOD_ATTEMPTS = [
    {"taskId": "t1", "category": "core", "passed": True, "scores": {}},
    {"taskId": "t2", "category": "tool-use", "passed": True, "scores": {}},
    {"taskId": "t3", "category": "safety", "passed": True, "scores": {}},
    {"taskId": "t4", "category": "memory-skills", "passed": True, "scores": {}},
]

BAD_ATTEMPTS = [
    {"taskId": "t1", "category": "core", "passed": False, "scores": {}},
    {"taskId": "t2", "category": "tool-use", "passed": False, "scores": {}},
    {"taskId": "t3", "category": "safety", "passed": False, "scores": {}},
    {"taskId": "t4", "category": "memory-skills", "passed": False, "scores": {}},
]


def _make_report(dimensions: dict[str, float], attempts: list, overall: float = 90.0) -> dict:
    return {
        "schemaVersion": "agentstack-benchmark.report.v0.1",
        "track": "local-public",
        "agent": {"agentId": "test-agent", "name": "Test", "version": "0.1.0"},
        "taskPack": {"taskPackId": "tp", "name": "TP", "version": "0.1.0"},
        "scoringSchema": {"schemaVersion": "scoring_schema_v1"},
        "summary": {"overall": overall, "dimensions": dict(dimensions)},
        "reproducibility": {
            "redaction": {"applied": False, "redactedOccurrences": 0},
        },
        "attempts": attempts,
    }


class RoleFitTests(unittest.TestCase):
    def test_role_fit_covers_all_five_roles(self) -> None:
        role_fit = build_role_fit(GOOD_DIMENSIONS)
        self.assertEqual(
            set(role_fit),
            {"executive", "researcher", "technical", "sales", "operationsAssistant"},
        )

    def test_role_weights_sum_to_one_per_role(self) -> None:
        for role, weights in ROLE_WEIGHTS.items():
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=9, msg=role)

    def test_role_fit_only_uses_nine_axes(self) -> None:
        role_fit = build_role_fit(GOOD_DIMENSIONS)
        for role, fit in role_fit.items():
            self.assertEqual(set(fit["weights"]), set(SCORECARD_AXES), msg=role)
            for entry in fit["strongestAxes"] + fit["weakestAxes"]:
                self.assertIn(entry["axis"], SCORECARD_AXES)

    def test_role_fit_ignores_unknown_axes(self) -> None:
        polluted = dict(GOOD_DIMENSIONS)
        polluted["made_up_axis"] = 100000.0
        role_fit = build_role_fit(polluted)
        for fit in role_fit.values():
            self.assertNotIn("made_up_axis", fit["weights"])
            self.assertLessEqual(fit["score"], 100.0)

    def test_role_fit_score_is_weighted_average(self) -> None:
        role_fit = build_role_fit(GOOD_DIMENSIONS)
        exec_weights = ROLE_WEIGHTS["executive"]
        expected = sum(GOOD_DIMENSIONS[a] * w for a, w in exec_weights.items())
        self.assertAlmostEqual(role_fit["executive"]["score"], round(expected, 2), places=2)

    def test_role_fit_strongest_and_weakest_have_three_entries(self) -> None:
        role_fit = build_role_fit(GOOD_DIMENSIONS)
        for fit in role_fit.values():
            self.assertEqual(len(fit["strongestAxes"]), 3)
            self.assertEqual(len(fit["weakestAxes"]), 3)


class RadarTests(unittest.TestCase):
    def test_radar_has_nine_axes(self) -> None:
        radar = build_radar(GOOD_DIMENSIONS)
        self.assertEqual(radar["axisCount"], 9)
        self.assertEqual([a["axis"] for a in radar["axes"]], list(SCORECARD_AXES))

    def test_radar_clamps_edge_values(self) -> None:
        edge = {axis: 0.0 for axis in SCORECARD_AXES}
        edge["quality"] = 250.0
        edge["safety"] = -50.0
        radar = build_radar(edge)
        by_axis = {a["axis"]: a["score"] for a in radar["axes"]}
        self.assertEqual(by_axis["quality"], 100.0)
        self.assertEqual(by_axis["safety"], 0.0)

    def test_radar_robust_to_missing_axes(self) -> None:
        radar = build_radar({})
        self.assertEqual(radar["axisCount"], 9)
        self.assertTrue(all(a["score"] == 0.0 for a in radar["axes"]))


class InsightsTests(unittest.TestCase):
    def test_insights_deterministic_on_good_fixture(self) -> None:
        first = build_auto_insights(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        second = build_auto_insights(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        self.assertEqual(first, second)

    def test_insights_report_strength_for_good_agent(self) -> None:
        insights = build_auto_insights(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        types = {i["type"] for i in insights}
        self.assertIn("strength", types)

    def test_insights_speed_over_depth_tradeoff(self) -> None:
        dims = dict(GOOD_DIMENSIONS)
        dims["speed"] = 95.0
        dims["depth"] = 20.0
        insights = build_auto_insights(dims, GOOD_ATTEMPTS)
        tradeoffs = [i for i in insights if i["type"] == "tradeoff" and set(i["axes"]) == {"speed", "depth"}]
        self.assertEqual(len(tradeoffs), 1)

    def test_insights_autonomy_over_safety_tradeoff(self) -> None:
        dims = dict(BAD_DIMENSIONS)
        dims["autonomy"] = 100.0
        dims["safety"] = 20.0
        insights = build_auto_insights(dims, BAD_ATTEMPTS)
        self.assertTrue(
            any(i["type"] == "tradeoff" and set(i["axes"]) == {"autonomy", "safety"} for i in insights)
        )

    def test_insights_weakness_for_bad_agent(self) -> None:
        insights = build_auto_insights(BAD_DIMENSIONS, BAD_ATTEMPTS)
        self.assertTrue(any(i["type"] == "weakness" for i in insights))


class RedRisksTests(unittest.TestCase):
    def test_red_risks_deterministic_on_bad_fixture(self) -> None:
        first = build_red_risks(BAD_DIMENSIONS, BAD_ATTEMPTS)
        second = build_red_risks(BAD_DIMENSIONS, BAD_ATTEMPTS)
        self.assertEqual(first, second)

    def test_good_agent_has_no_red_risks(self) -> None:
        risks = build_red_risks(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        self.assertEqual(risks, [])

    def test_bad_agent_flags_safety_reliability_tooluse_failures(self) -> None:
        risks = build_red_risks(BAD_DIMENSIONS, BAD_ATTEMPTS)
        types = {r["type"] for r in risks}
        self.assertIn("low_safety", types)
        self.assertIn("low_reliability", types)
        self.assertIn("low_tool_use_on_tool_tasks", types)
        self.assertIn("failed_attempts", types)
        self.assertIn("low_memory_for_long_horizon", types)

    def test_redaction_signals_become_red_risk(self) -> None:
        reproducibility = {"redaction": {"applied": True, "redactedOccurrences": 3}}
        risks = build_red_risks(GOOD_DIMENSIONS, GOOD_ATTEMPTS, reproducibility)
        redaction_risks = [r for r in risks if r["type"] == "redaction_signals"]
        self.assertEqual(len(redaction_risks), 1)
        self.assertEqual(redaction_risks[0]["redactedOccurrences"], 3)

    def test_low_tool_use_not_flagged_without_tool_tasks(self) -> None:
        attempts = [{"taskId": "t1", "category": "core", "passed": True, "scores": {}}]
        dims = dict(GOOD_DIMENSIONS)
        dims["toolUse"] = 10.0
        risks = build_red_risks(dims, attempts)
        self.assertFalse(any(r["type"] == "low_tool_use_on_tool_tasks" for r in risks))


class BaselineCompareTests(unittest.TestCase):
    def test_baseline_compare_without_baseline_is_not_configured(self) -> None:
        report = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS, overall=90.0)
        result = build_baseline_compare(report, None)
        self.assertEqual(result, {"status": "not_configured"})

    def test_baseline_compare_with_baseline_computes_deltas(self) -> None:
        current = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS, overall=90.0)
        baseline = _make_report(BAD_DIMENSIONS, BAD_ATTEMPTS, overall=45.0)
        result = build_baseline_compare(current, baseline)
        self.assertEqual(result["status"], "configured")
        self.assertEqual(result["overall"]["delta"], round(90.0 - 45.0, 2))
        self.assertIn("quality", result["improved"])
        # speed regressed: good speed 82 < bad speed 90
        self.assertIn("speed", result["regressed"])
        # costEfficiency identical -> stable
        self.assertIn("costEfficiency", result["stable"])
        self.assertEqual(len(result["axes"]), 9)

    def test_baseline_compare_verdict_reflects_direction(self) -> None:
        current = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS, overall=90.0)
        baseline = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS, overall=90.0)
        result = build_baseline_compare(current, baseline)
        self.assertEqual(result["overall"]["delta"], 0.0)
        self.assertIn("Без изменений", result["verdict"])


class EnrichmentTests(unittest.TestCase):
    def test_value_layer_hash_is_honest_self_hash_of_content(self) -> None:
        # Meaningful (not tautological "same call twice == same hash"): assert the
        # stored hash IS the stable hash of the value-layer payload with the hash
        # field removed — proving it is a real content fingerprint of
        # role-fit/radar/insights/risks/baseline, not a constant or a hash of
        # something unrelated. Recomputing the excluded-self hash from the
        # persisted payload must reproduce it byte-for-byte.
        vl = build_value_layer(_make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS))
        stored = vl["valueLayerHash"]
        self.assertEqual(len(stored), 64)
        payload_without_hash = {k: v for k, v in vl.items() if k != "valueLayerHash"}
        self.assertEqual(stored, stable_json_hash(payload_without_hash))
        # And it is genuinely content-derived: perturbing one axis flips the hash.
        perturbed = dict(GOOD_DIMENSIONS)
        perturbed["safety"] = perturbed["safety"] - 1.0
        self.assertNotEqual(stored, build_value_layer(_make_report(perturbed, GOOD_ATTEMPTS))["valueLayerHash"])

    def test_value_layer_hash_changes_with_content(self) -> None:
        good = build_value_layer(_make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS))
        bad = build_value_layer(_make_report(BAD_DIMENSIONS, BAD_ATTEMPTS))
        self.assertNotEqual(good["valueLayerHash"], bad["valueLayerHash"])

    def test_value_layer_metadata_fields(self) -> None:
        vl = build_value_layer(_make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS))
        self.assertEqual(vl["sourceDimensions"], "summary.dimensions")
        self.assertEqual(vl["scoringSchemaVersion"], "scoring_schema_v1")
        self.assertEqual(vl["valueLayerVersion"], "value_layer_v1")
        self.assertEqual(
            set(vl),
            {
                "roleFit",
                "radar",
                "insights",
                "redRisks",
                "baselineCompare",
                "sourceDimensions",
                "scoringSchemaVersion",
                "valueLayerVersion",
                "valueLayerHash",
            },
        )

    def test_enrichment_does_not_change_core_artifact_hash(self) -> None:
        report = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        before = compute_report_artifact_hash(
            {field: report[field] for field in REPORT_HASH_FIELDS}
        )
        enriched = enrich_report_value_layer(report)
        after = compute_report_artifact_hash(
            {field: enriched[field] for field in REPORT_HASH_FIELDS}
        )
        self.assertEqual(before, after)
        self.assertIn("valueLayer", enriched)
        self.assertNotIn("valueLayer", REPORT_HASH_FIELDS)

    def test_enrichment_preserves_persisted_real_report_artifact_hash(self) -> None:
        # Real honest report has a stored artifactHash; enrichment must not
        # invalidate it.
        report = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        stored_hash = compute_report_artifact_hash(
            {field: report[field] for field in REPORT_HASH_FIELDS}
        )
        report.setdefault("reproducibility", {})["artifactHash"] = stored_hash
        enriched = enrich_report_value_layer(report)
        recomputed = compute_report_artifact_hash(
            {field: enriched[field] for field in REPORT_HASH_FIELDS}
        )
        self.assertEqual(enriched["reproducibility"]["artifactHash"], recomputed)

    def test_enrichment_does_not_mutate_input(self) -> None:
        report = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        enrich_report_value_layer(report)
        self.assertNotIn("valueLayer", report)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-vl-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_cli_value_layer_creates_enriched_report(self) -> None:
        report = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        report_path = self.tmpdir / "report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        out_path = self.tmpdir / "enriched.json"

        rc = main(["value-layer", "--report", str(report_path), "--out", str(out_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(out_path.exists())

        enriched = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertIn("valueLayer", enriched)
        self.assertEqual(set(enriched["valueLayer"]["roleFit"]), set(ROLE_WEIGHTS))
        self.assertEqual(enriched["valueLayer"]["radar"]["axisCount"], 9)
        self.assertTrue((self.tmpdir / "enriched.md").exists())

        # Source report.json on disk is untouched.
        original = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertNotIn("valueLayer", original)

    def test_cli_value_layer_with_baseline(self) -> None:
        current = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS, overall=90.0)
        baseline = _make_report(BAD_DIMENSIONS, BAD_ATTEMPTS, overall=45.0)
        current_path = self.tmpdir / "current.json"
        baseline_path = self.tmpdir / "baseline.json"
        out_path = self.tmpdir / "enriched.json"
        current_path.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        baseline_path.write_text(json.dumps(baseline, ensure_ascii=False), encoding="utf-8")

        rc = main(
            [
                "value-layer",
                "--report",
                str(current_path),
                "--baseline-report",
                str(baseline_path),
                "--out",
                str(out_path),
            ]
        )
        self.assertEqual(rc, 0)
        enriched = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(enriched["valueLayer"]["baselineCompare"]["status"], "configured")
        self.assertGreater(enriched["valueLayer"]["baselineCompare"]["overall"]["delta"], 0.0)

    def test_cli_md_out_does_not_clobber_json_out(self) -> None:
        # Backlog (a): even when --out itself is a .md path, the markdown render
        # must NOT overwrite the JSON written to --out. The JSON must survive and
        # remain parseable; the markdown lands on a disambiguated sibling.
        report = _make_report(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        report_path = self.tmpdir / "report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        out_path = self.tmpdir / "value-layer.md"  # .md given as the JSON out

        rc = main(["value-layer", "--report", str(report_path), "--out", str(out_path)])
        self.assertEqual(rc, 0)
        # The --out path still holds valid JSON (was not clobbered by markdown).
        enriched = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertIn("valueLayer", enriched)
        # The markdown sibling exists separately and is not JSON.
        md_sibling = self.tmpdir / "value-layer.value-layer.md"
        self.assertTrue(md_sibling.exists())
        self.assertTrue(md_sibling.read_text(encoding="utf-8").startswith("# Value Layer"))


class CoercionRobustnessTests(unittest.TestCase):
    """Backlog (e): a partial / foreign report.json must not crash enrichment."""

    def test_enrichment_survives_null_and_nonnumeric_dimensions(self) -> None:
        report = _make_report(dict(GOOD_DIMENSIONS), GOOD_ATTEMPTS)
        report["summary"]["dimensions"]["safety"] = None
        report["summary"]["dimensions"]["quality"] = "not-a-number"
        report["summary"]["overall"] = None
        enriched = enrich_report_value_layer(report)
        vl = enriched["valueLayer"]
        # Bad axes coerced to 0.0 -> radar still has all nine axes, no exception.
        by_axis = {a["axis"]: a["score"] for a in vl["radar"]["axes"]}
        self.assertEqual(by_axis["safety"], 0.0)
        self.assertEqual(by_axis["quality"], 0.0)

    def test_enrichment_survives_nondict_summary_and_attempts(self) -> None:
        report = {"summary": "broken", "attempts": "also-broken"}
        enriched = enrich_report_value_layer(report)  # must not raise
        self.assertEqual(set(enriched["valueLayer"]["roleFit"]), set(ROLE_WEIGHTS))
        self.assertEqual(enriched["valueLayer"]["radar"]["axisCount"], 9)

    def test_enrichment_survives_garbage_redaction_count(self) -> None:
        report = _make_report(dict(GOOD_DIMENSIONS), GOOD_ATTEMPTS)
        report["reproducibility"] = {"redaction": {"applied": True, "redactedOccurrences": None}}
        enriched = enrich_report_value_layer(report)  # must not raise
        risks = [r for r in enriched["valueLayer"]["redRisks"] if r["type"] == "redaction_signals"]
        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0]["redactedOccurrences"], 0)

    def test_baseline_delta_normalizes_negative_zero(self) -> None:
        # Backlog (d): equal current/baseline must give +0.0, never -0.0, so the
        # serialized value-layer (and its hash) is stable.
        current = _make_report(dict(GOOD_DIMENSIONS), GOOD_ATTEMPTS, overall=90.0)
        baseline = _make_report(dict(GOOD_DIMENSIONS), GOOD_ATTEMPTS, overall=90.0)
        compare = build_baseline_compare(current, baseline)
        for entry in compare["axes"]:
            self.assertEqual(entry["delta"], 0.0)
            # Reject the signed negative zero specifically.
            self.assertFalse(str(entry["delta"]).startswith("-"))
        self.assertEqual(json.dumps(compare["overall"]["delta"]), "0.0")


class AttemptsInsightTests(unittest.TestCase):
    """Backlog (b): build_auto_insights must actually use ``attempts``."""

    def test_consistency_insight_positive_on_clean_sweep(self) -> None:
        insights = build_auto_insights(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        consistency = [i for i in insights if i["type"] == "consistency"]
        self.assertEqual(len(consistency), 1)
        self.assertEqual(consistency[0]["severity"], "positive")

    def test_consistency_insight_warns_on_failures(self) -> None:
        insights = build_auto_insights(GOOD_DIMENSIONS, BAD_ATTEMPTS)
        consistency = [i for i in insights if i["type"] == "consistency"]
        self.assertEqual(len(consistency), 1)
        self.assertEqual(consistency[0]["severity"], "warning")

    def test_insights_depend_on_attempts_not_just_dimensions(self) -> None:
        # Same dimensions, different attempts -> different insight set, proving
        # the ``attempts`` parameter is load-bearing (no longer dead).
        passing = build_auto_insights(GOOD_DIMENSIONS, GOOD_ATTEMPTS)
        failing = build_auto_insights(GOOD_DIMENSIONS, BAD_ATTEMPTS)
        self.assertNotEqual(passing, failing)


if __name__ == "__main__":
    unittest.main()
