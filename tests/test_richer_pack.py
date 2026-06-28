"""Covering tests for the Richer v1 task pack (P6).

Pure data/contract tests: they assert the richer pack is schema-valid, balanced
across all nine scored axes, ships a sealed hidden anti-cheat subset that the
local-public runner rejects, and hashes stably. They do NOT exercise or modify
the frozen scoring code — only the pack data and the existing validators.
"""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from agentstack_benchmark.runner import _validate_task_pack
from agentstack_benchmark.schemas import stable_json_hash
from agentstack_benchmark.tracks import validate_local_public_task_pack

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PACK_PATH = PROJECT_ROOT / "examples/task_packs/richer_v1.json"
HIDDEN_PACK_PATH = PROJECT_ROOT / "examples/task_packs/richer_v1_hidden.json"

# The nine weighted scorecard axes (must match evaluator.SCORING_WEIGHTS keys).
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
# Categories the scorer routes on (evaluator._deterministic_passed / *_score).
VALID_CATEGORIES = {"core", "safety", "tool-use", "memory-skills"}
VALID_EXPECTED_TYPES = {"contains", "equals", "regex"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RicherPackStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.public = _load(PUBLIC_PACK_PATH)
        cls.hidden = _load(HIDDEN_PACK_PATH)

    def test_public_pack_is_schema_valid(self) -> None:
        # Runner's structural validator must accept it (taskPackId/name/version/
        # tasks + per-task taskId/prompt/expected), and every task must carry the
        # richer metadata (axis/category/expected.type) the scorer relies on.
        _validate_task_pack(self.public)
        for task in self.public["tasks"]:
            self.assertIn("axis", task, task.get("taskId"))
            self.assertIn(task["axis"], SCORED_AXES, task["taskId"])
            self.assertIn(task.get("category"), VALID_CATEGORIES, task["taskId"])
            self.assertIn(task["expected"]["type"], VALID_EXPECTED_TYPES, task["taskId"])

    def test_public_pack_has_rich_task_count(self) -> None:
        # "Richer" target band: substantially deeper than the 5-task mvp_v0.
        self.assertGreaterEqual(len(self.public["tasks"]), 15)
        self.assertLessEqual(len(self.public["tasks"]), 30)
        ids = [t["taskId"] for t in self.public["tasks"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate taskIds in public pack")

    def test_public_pack_covers_all_nine_axes(self) -> None:
        axes = {t["axis"] for t in self.public["tasks"]}
        self.assertTrue(
            SCORED_AXES.issubset(axes),
            f"missing axes: {sorted(SCORED_AXES - axes)}",
        )
        # Balanced-ish: no single axis dominates the whole pack.
        counts = Counter(t["axis"] for t in self.public["tasks"])
        self.assertLessEqual(
            max(counts.values()),
            len(self.public["tasks"]) // 2,
            f"one axis dominates the pack: {dict(counts)}",
        )

    def test_public_pack_runs_on_local_public_track(self) -> None:
        # No hidden tasks leak into the runnable public pack -> validator accepts.
        validate_local_public_task_pack(self.public)
        for task in self.public["tasks"]:
            self.assertFalse(task.get("hidden", False), task["taskId"])
            self.assertNotEqual(task.get("visibility"), "hidden", task["taskId"])

    def test_objective_oracles_are_robust_not_brittle(self) -> None:
        # P5 lesson: objective oracles use regex (found anywhere in the answer,
        # robust to surrounding prose), never a brittle full-answer ``equals``.
        for task in self.public["tasks"]:
            self.assertNotEqual(
                task["expected"]["type"],
                "equals",
                f"{task['taskId']} uses brittle equals oracle",
            )

    def test_depth_keywords_present_where_useful(self) -> None:
        # Depth axis is scored from depthKeywords; the depth-axis tasks must carry
        # them, and the pack overall must use them on a meaningful share of tasks.
        with_depth = [t for t in self.public["tasks"] if t.get("depthKeywords")]
        self.assertGreaterEqual(len(with_depth), len(self.public["tasks"]) // 2)
        for task in self.public["tasks"]:
            if task["axis"] == "depth":
                self.assertTrue(task.get("depthKeywords"), task["taskId"])


class RicherHiddenSubsetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.public = _load(PUBLIC_PACK_PATH)
        cls.hidden = _load(HIDDEN_PACK_PATH)

    def test_hidden_subset_exists_and_is_nonempty(self) -> None:
        self.assertTrue(HIDDEN_PACK_PATH.exists())
        self.assertGreaterEqual(len(self.hidden["tasks"]), 1)
        # The public pack points at the sealed sibling.
        self.assertEqual(
            self.public.get("hiddenSubsetRef"),
            "examples/task_packs/richer_v1_hidden.json",
        )

    def test_every_hidden_task_is_sealed(self) -> None:
        for task in self.hidden["tasks"]:
            self.assertTrue(task.get("hidden"), task["taskId"])
            self.assertEqual(task.get("visibility"), "hidden", task["taskId"])
            self.assertEqual(task.get("requiresTrack"), "hosted-verified", task["taskId"])

    def test_local_public_runner_rejects_hidden_subset(self) -> None:
        with self.assertRaisesRegex(ValueError, "hidden tasks require hosted-verified"):
            validate_local_public_task_pack(self.hidden)

    def test_hidden_ids_do_not_leak_into_public_pack(self) -> None:
        public_ids = {t["taskId"] for t in self.public["tasks"]}
        hidden_ids = {t["taskId"] for t in self.hidden["tasks"]}
        self.assertEqual(public_ids & hidden_ids, set())

    def test_full_pack_covers_nine_axes(self) -> None:
        axes = {t["axis"] for t in self.public["tasks"]}
        axes |= {t["axis"] for t in self.hidden["tasks"]}
        self.assertTrue(SCORED_AXES.issubset(axes))


class RicherPackHashStabilityTests(unittest.TestCase):
    def test_pack_hashes_are_stable_and_distinct(self) -> None:
        public = _load(PUBLIC_PACK_PATH)
        hidden = _load(HIDDEN_PACK_PATH)
        # Stable: hashing the same content twice is identical (reproducibility).
        self.assertEqual(stable_json_hash(public), stable_json_hash(public))
        self.assertEqual(stable_json_hash(hidden), stable_json_hash(hidden))
        # Distinct: public and hidden packs are different artifacts.
        self.assertNotEqual(stable_json_hash(public), stable_json_hash(hidden))

    def test_pack_hash_is_order_independent_for_keys(self) -> None:
        # stable_json_hash sorts keys, so a re-serialized (reordered) copy hashes
        # identically — the property the report's taskPackHash depends on.
        public = _load(PUBLIC_PACK_PATH)
        reordered = json.loads(json.dumps(public, sort_keys=True))
        self.assertEqual(stable_json_hash(public), stable_json_hash(reordered))


if __name__ == "__main__":
    unittest.main()
