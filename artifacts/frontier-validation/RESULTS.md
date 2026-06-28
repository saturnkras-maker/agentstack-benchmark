# Frontier v1 validation — strong-judge top-tier separation (P7)

Real local Claude runs (subscription, ANTHROPIC_* stripped, loopback HTTP adapters)
on `examples/task_packs/frontier_v1.json`, graded by the **strong** gradient judge
`--judge-model claude-sonnet-4-6` with per-task `judgeRubric` (0–100 by depth/rigour).

## Canonical leaderboard (run2, agent call-timeout 175s)

| rank | agent                         | overall | passed |
|------|-------------------------------|---------|--------|
| 1    | Claude Code (Opus 4.8) — real   | **90.02** | 12/12 |
| 2    | Claude Code (Sonnet 4.6) — real | **88.95** | 12/12 |
| 3    | Claude Code (Haiku 4.5) — real  | **86.42** | 12/12 |
| 4    | Haiku handicapped weak (≤5 words) | **60.69** | 7/12  |

Source reports: `run2/<tier>/report.json`, leaderboard: `run2/leaderboard.json`.

### Verdict
- **Frontier-vs-weak separation: decisive.** The weak handicap agent lands ~26 pts
  below Opus and only passes 7/12 — its ≤5-word answers cannot carry depth, scoring
  2–22 on every judged depth task.
- **Top-tier order: correct and defensible.** Opus ≥ Sonnet ≥ Haiku, monotonic.
  The original P-state defect (Opus 83 < Haiku 87 under haiku-judge + richer_v1) is
  fixed here: a STRONG judge with GRADIENT rubrics resolves the order that a weak
  pass/fail judge collapses.

### Where the tiers actually separate (judged depth tasks, quality 0–100)
| task | opus | sonnet | haiku | weak |
|------|------|--------|-------|------|
| fd_ambiguous_spec_edgecases | 97 | 92 | 72 | 8 |
| fd_distributed_tradeoff     | 97 | 97 | 88 | 2 |
| fa_longhorizon_plan         | 97 | 95 | 82 | 8 |
| fr_subtle_bug_hunt          | 97 | 97 | 95 | 12 |
| fc_precise_concise          | 72 | 72 | 72 | 22 |

Objective anchors (probability/rate/logic/state/fast token) are solved 100 by all
three strong tiers — they are NOT the separators, but they are real: in the
first pass (`run-*.log` first batch) the rate task caught a genuine Sonnet
arithmetic slip and the state-chain task caught a Sonnet letter-count error, so
the anchors do fail surface-plausible-but-wrong answers as intended.

## Honest caveats (no fabrication)
1. **Margins among strong tiers are modest** (90.0 / 89.0 / 86.4). The order is
   correct and monotonic, but Opus↔Sonnet is ~1.1 pt — the separation is real but
   not huge. Depth tasks separate cleanly; objective anchors and the fast/cost
   tasks (which all tiers ace) compress the spread.
2. **Transport-timeout artifact (first pass, 110s).** With the agent call-timeout
   at 110s, the long-horizon plan task TIMED OUT for the longest-writing tiers
   (Opus, Haiku), zeroing that task and inverting Sonnet↔Haiku (run1: Opus 83.2,
   Haiku 82.5, Sonnet 82.3). Raising the agent call-timeout to 175s (per the P7
   brief, frontier answers are long) let every tier complete and produced the
   clean run2 ranking above. The fix is the transport timeout, NOT the pack/judge.
3. **Judge is Sonnet-tier.** Opus answers are graded by a Sonnet judge, so any
   Opus superiority that exceeds Sonnet's own ceiling is under-counted (the very
   evaluator-ceiling effect task `fc_precise_concise` describes). Opus still ranks
   first; an Opus judge could widen the Opus↔Sonnet gap but was not required to
   achieve a correct order.

## Reproducibility
Judge verdicts are cached in `judge-cache-sonnet.json` keyed by
(taskId, model, normalized answer, rubric); re-running identical answers reproduces
byte-identical verdicts. Reports carry `scoringSchemaV2` (non-deterministic, cached)
alongside the frozen `scoring_schema_v1`.
