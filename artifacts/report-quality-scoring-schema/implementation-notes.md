# Report quality + scoring_schema_v1 slice

## Scope

Autonomous v2 mode active. This slice implements the next critical-path item after adapter contract: report quality + scoring_schema_v1.

In scope:

- freeze the current deterministic scoring weights as `scoring_schema_v1`;
- include the scoring schema metadata in report JSON with stable top-level order;
- improve Markdown report readability with track/schema/scorecard/task-score breakdown;
- tests for schema presence, order, weights, and Markdown report quality.

Out of scope:

- changing scoring weights or task scoring formula;
- LLM-as-judge;
- reproducibility/redaction hashes;
- hidden/verified track;
- auth/rate limits;
- external deploy/public launch/billing/live external actions/private-key flows.

## Preflight

- `git status --short --branch` → `## main`
- latest commit: `fa0a3db feat: define http adapter contract`
- repo clean before edits.
- inspected: evaluator, runner report rendering, runner tests.

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_report_declares_scoring_schema_v1_with_canonical_order -v`
  - expected failure: `ImportError: cannot import name 'SCORING_SCHEMA_VERSION'`.

## Implementation decisions

- Froze deterministic local-public beta scoring as `scoring_schema_v1`.
- Added `SCORING_SCHEMA_VERSION`, `SCORING_WEIGHTS`, `SCORING_VERDICTS`, and `build_scoring_schema()` in the evaluator.
- Kept existing score formulas and weights unchanged; this slice documents/freezes the current schema instead of recalibrating it.
- Report JSON now embeds top-level `scoringSchema` between `taskPack` and `summary`.
- Canonical report prefix is now: `schemaVersion`, `track`, `agent`, `taskPack`, `scoringSchema`, `summary`.
- Markdown reports now include track, scoring schema version, weighted scorecard dimensions, and per-task score breakdowns.
- Added `docs/scoring-schema-v1.md` and README notes.
- Explicitly kept LLM-as-judge, hidden tasks, hosted verification, auth/rate limits, deploy, launch, billing, and reproducibility/redaction out of this slice.

## GREEN / verification

- Targeted runner tests:
  - `PYTHONPATH=src python3 -m unittest tests.test_runner -v`
  - result: `Ran 10 tests in 2.399s` / `OK`.
- Full suite + compile gate:
  - `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 23 tests in 8.753s` / `OK`; compile gate exit `0`.
- Manual report smoke:
  - command: local CLI run with `mock_good.json` and `mvp_v0.json` into `/tmp/agentstack-report-quality-smoke/run`.
  - observed:
    - `top_order=schemaVersion,track,agent,taskPack,scoringSchema,summary`
    - `scoring_schema=scoring_schema_v1`
    - `weights_total=1.00`
    - `track=local-public`
    - `overall=98.83`
    - `markdown_has_scorecard=True`
    - `markdown_has_task_scores=True`
  - temp smoke directory removed.
