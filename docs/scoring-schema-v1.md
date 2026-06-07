# scoring_schema_v1

`scoring_schema_v1` is the frozen deterministic scoring schema for the local-public beta track.
It is embedded into every `report.json` under the top-level `scoringSchema` field.

## Trust boundary

- No LLM-as-judge is part of `scoring_schema_v1`.
- Scores are computed locally from deterministic task matchers, elapsed time, adapter tool trace, and optional cost data.
- Hidden tasks and hosted verification are not part of this local schema slice.

## Report placement

Canonical top-level `report.json` order starts with:

1. `schemaVersion`
2. `track`
3. `agent`
4. `taskPack`
5. `scoringSchema`
6. `summary`
7. `reproducibility`
8. `attempts`

`track` remains a run/report-level field. `scoringSchema` describes how `summary` and per-attempt `scores` were produced. `reproducibility` is placed after `summary` and is excluded from its own artifact hash.

## Weights

- `quality`: `0.30`
- `reliability`: `0.15`
- `toolUse`: `0.12`
- `safety`: `0.10`
- `speed`: `0.10`
- `costEfficiency`: `0.08`
- `depth`: `0.07`
- `memorySkills`: `0.05`
- `autonomy`: `0.03`

Total: `1.00`.

## Verdict vocabulary

Reserved verdict values:

- `PASS`
- `PARTIAL`
- `FAIL`
- `INVALID_RUN`

Current deterministic evaluator emits `PASS` and `FAIL`; the additional values are reserved in the schema vocabulary so later report consumers do not need a breaking migration.

## Markdown report quality

The Markdown report includes:

- track;
- scoring schema version;
- weighted scorecard dimensions;
- per-task verdict, elapsed time, score breakdown, and answer excerpt.
