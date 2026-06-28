"""Covering tests for the Frontier v1 task pack (P7).

Pure data/contract tests over the frontier pack and the judge's gradient-rubric
plumbing. They assert the pack is schema-valid, runs on the local-public track,
spans the nine scored axes, uses robust (non-brittle) objective oracles, and —
crucially for P7 — that its open tasks carry a per-task GRADIENT ``judgeRubric``
that the judge actually wraps in the discriminating gradient prompt. They do NOT
exercise the frozen deterministic scorer, only pack data and existing validators
plus the judge's pure rubric-selection helper.
"""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from agentstack_benchmark.judge import (
    _GRADIENT_RUBRIC_FOOTER,
    _GRADIENT_RUBRIC_HEADER,
    _RUBRIC,
    _effective_rubric,
)
from agentstack_benchmark.runner import _validate_task_pack
from agentstack_benchmark.schemas import stable_json_hash
from agentstack_benchmark.tracks import validate_local_public_task_pack

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTIER_PACK_PATH = PROJECT_ROOT / "examples/task_packs/frontier_v1.json"

SCORED_AXES = {
    "quality",
    "reliability",
    "toolUse",
    "safety",
    "speed",
    "costEfficiency",
    "depth",
    "memorySkills",
    "autonomy",
}
VALID_CATEGORIES = {"core", "safety", "tool-use", "memory-skills"}
VALID_EXPECTED_TYPES = {"contains", "equals", "regex"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FrontierPackStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = _load(FRONTIER_PACK_PATH)

    def test_pack_is_schema_valid(self) -> None:
        _validate_task_pack(self.pack)
        for task in self.pack["tasks"]:
            self.assertIn("axis", task, task.get("taskId"))
            self.assertIn(task["axis"], SCORED_AXES, task["taskId"])
            self.assertIn(task.get("category"), VALID_CATEGORIES, task["taskId"])
            self.assertIn(task["expected"]["type"], VALID_EXPECTED_TYPES, task["taskId"])

    def test_pack_runs_until_completion_sized_band(self) -> None:
        # Frontier target band: ~8-12 tasks so a real strong-judge validation run
        # actually finishes within a sane wall-clock budget (P7 brief: don't bloat
        # it or the run gets killed on time).
        self.assertGreaterEqual(len(self.pack["tasks"]), 8)
        self.assertLessEqual(len(self.pack["tasks"]), 14)
        ids = [t["taskId"] for t in self.pack["tasks"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate taskIds in frontier pack")

    def test_pack_covers_all_nine_axes(self) -> None:
        axes = {t["axis"] for t in self.pack["tasks"]}
        self.assertTrue(
            SCORED_AXES.issubset(axes),
            f"missing axes: {sorted(SCORED_AXES - axes)}",
        )
        counts = Counter(t["axis"] for t in self.pack["tasks"])
        self.assertLessEqual(
            max(counts.values()),
            len(self.pack["tasks"]) // 2,
            f"one axis dominates the pack: {dict(counts)}",
        )

    def test_runs_on_local_public_track(self) -> None:
        validate_local_public_task_pack(self.pack)
        for task in self.pack["tasks"]:
            self.assertFalse(task.get("hidden", False), task["taskId"])
            self.assertNotEqual(task.get("visibility"), "hidden", task["taskId"])

    def test_objective_oracles_are_robust_not_brittle(self) -> None:
        # P5 lesson: objective anchors use regex found anywhere in the answer,
        # never a brittle full-answer equals.
        for task in self.pack["tasks"]:
            self.assertNotEqual(
                task["expected"]["type"],
                "equals",
                f"{task['taskId']} uses brittle equals oracle",
            )

    def test_has_objective_anchors_with_single_correct_answer(self) -> None:
        # Frontier separation relies on objective-anchor tasks where the
        # surface-plausible answer is wrong: at least a few regex-anchored tasks.
        regex_anchors = [t for t in self.pack["tasks"] if t["expected"]["type"] == "regex"]
        self.assertGreaterEqual(len(regex_anchors), 3, "too few objective anchors")


class FrontierGradientRubricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = _load(FRONTIER_PACK_PATH)

    def test_judged_tasks_carry_gradient_rubric(self) -> None:
        # Every explicitly-judged open task must ship a per-task judgeRubric so the
        # STRONG judge can discriminate depth (the whole point of P7). The rubric
        # must reference a gradient (mention high/low score bands), not pass/fail.
        judged = [t for t in self.pack["tasks"] if t.get("judge") is True]
        self.assertGreaterEqual(len(judged), 5, "frontier needs several judged depth tasks")
        for task in judged:
            rubric = task.get("judgeRubric")
            self.assertIsInstance(rubric, str, task["taskId"])
            self.assertTrue(rubric and rubric.strip(), task["taskId"])
            # A gradient rubric names what raises vs lowers the score (banded),
            # not a binary check. Heuristic: it must mention a high band marker.
            self.assertRegex(
                rubric,
                r"(90\+|9[05]\b|top[- ]tier|gradient|cap at|<40|50-69|70-89)",
                f"{task['taskId']} judgeRubric is not gradient-styled",
            )

    def test_effective_rubric_wraps_task_rubric_for_judged_tasks(self) -> None:
        # The judge's rubric selector must wrap a task's judgeRubric inside the
        # GRADIENT header/footer so the model is told to spread 0-100 by depth.
        for task in self.pack["tasks"]:
            effective = _effective_rubric(task)
            if task.get("judgeRubric"):
                self.assertIn(_GRADIENT_RUBRIC_HEADER, effective, task["taskId"])
                self.assertIn(_GRADIENT_RUBRIC_FOOTER, effective, task["taskId"])
                self.assertIn(task["judgeRubric"].strip(), effective, task["taskId"])
            else:
                # No custom rubric -> falls back to the unchanged default rubric.
                self.assertEqual(effective, _RUBRIC, task["taskId"])

    def test_default_rubric_unchanged_for_tasks_without_rubric(self) -> None:
        # A task with no judgeRubric (any legacy pack) must keep the original
        # pass/fail-leaning rubric verbatim, so existing packs are not perturbed.
        self.assertEqual(_effective_rubric({"taskId": "x"}), _RUBRIC)
        self.assertEqual(_effective_rubric({"taskId": "x", "judgeRubric": "   "}), _RUBRIC)

    def test_depth_keywords_present_on_judged_and_depth_tasks(self) -> None:
        for task in self.pack["tasks"]:
            if task["axis"] == "depth" or task.get("judge") is True:
                self.assertTrue(task.get("depthKeywords"), task["taskId"])


class FrontierPackHashStabilityTests(unittest.TestCase):
    def test_pack_hash_is_stable_and_order_independent(self) -> None:
        pack = _load(FRONTIER_PACK_PATH)
        self.assertEqual(stable_json_hash(pack), stable_json_hash(pack))
        reordered = json.loads(json.dumps(pack, sort_keys=True))
        self.assertEqual(stable_json_hash(pack), stable_json_hash(reordered))


if __name__ == "__main__":
    unittest.main()
