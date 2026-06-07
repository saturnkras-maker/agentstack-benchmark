# Reproducibility + redaction slice

## Scope

Autonomous v2 mode active. This slice implements the next critical-path item after report quality + `scoring_schema_v1`: reproducibility/redaction.

In scope:

- canonical SHA-256 report artifact hash that includes run-level `track`;
- explicit hash input fields and reproducibility metadata in `report.json`;
- deterministic variance + confidence band metadata from local task scores;
- report-output redaction for secret-like adapter answers/tool traces before JSON/Markdown persistence;
- tests and docs for the above.

Out of scope:

- hosted verification;
- hidden tasks;
- auth/rate limits;
- external deploy/public launch/billing/live external actions/private-key flows;
- executing arbitrary third-party agent code outside local test-controlled fixtures.

## Preflight

- `git status --short --branch` → `## main`
- latest commit: `583b535 feat: freeze scoring schema v1`
- repo clean before edits.
- inspected: `schemas.py`, `evaluator.py`, `runner.py`, existing runner tests.

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_report_contains_reproducibility_hash_that_depends_on_track -v`
  - expected failure: `ModuleNotFoundError: No module named 'agentstack_benchmark.reproducibility'`.

## Implementation decisions

- Added `agentstack_benchmark.reproducibility` with:
  - canonical report hash fields: `schemaVersion`, `track`, `agent`, `taskPack`, `scoringSchema`, `summary`, `attempts`;
  - SHA-256 artifact hash over those fields;
  - task-score variance and 95% confidence band;
  - recursive redaction for secret-like key/value strings.
- Kept `reproducibility` out of its own artifact hash to avoid recursive hashing.
- Kept `track` in the artifact hash input as required by v2.
- Scoring still runs on raw adapter output first; persisted attempts are redacted afterward so safety scoring can still detect leaks.
- Report top-level order is now: `schemaVersion`, `track`, `agent`, `taskPack`, `scoringSchema`, `summary`, `reproducibility`, `attempts`.
- Markdown reports now include a reproducibility section with artifact hash, confidence band, and redaction count.
- Added `docs/reproducibility-redaction.md` and README notes.
- Explicitly kept hosted verification, hidden tasks, auth/rate limits, deploy, launch, billing, and arbitrary external/private-key code execution out of this slice.

## GREEN / verification

- Targeted runner tests:
  - `PYTHONPATH=src python3 -m unittest tests.test_runner -v`
  - result: `Ran 13 tests in 2.626s` / `OK`.
- Full suite + compile gate:
  - `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 26 tests in 9.107s` / `OK`; compile gate exit `0`.
- Manual reproducibility/redaction smoke:
  - command: local CLI run with a temp local leaky fixture agent and temp task pack.
  - observed:
    - `top_order=schemaVersion,track,agent,taskPack,scoringSchema,summary,reproducibility,attempts`
    - `artifact_hash_len=64`
    - `hash_fields=schemaVersion,track,agent,taskPack,scoringSchema,summary,attempts`
    - `confidence={'confidenceLevel': 0.95, 'method': 'normal_approximation_over_task_weighted_scores', 'lower': 98.58, 'upper': 98.58}`
    - `redacted_occurrences=3`
    - `has_manual_secret=False`
  - temp smoke directory removed.
