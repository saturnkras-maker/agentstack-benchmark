# Reproducibility and redaction

This slice adds local-public beta reproducibility metadata to every generated `report.json` and keeps secret-like adapter output out of persisted report artifacts.

## What is included in `report.json`

Top-level report order now includes:

1. `schemaVersion`
2. `track`
3. `agent`
4. `taskPack`
5. `scoringSchema`
6. `summary`
7. `reproducibility`
8. `attempts`

The `reproducibility` object contains:

- `hashAlgorithm`: currently `sha256`.
- `artifactHash`: SHA-256 over canonical hash input fields.
- `hashFields`: fields included in the canonical hash input.
- `scoreStats`: local variance and confidence-band metadata.
- `redaction`: whether secret-like output was redacted before persistence.

## Hash input

The canonical hash input includes run-level `track`:

1. `schemaVersion`
2. `track`
3. `agent`
4. `taskPack`
5. `scoringSchema`
6. `summary`
7. `attempts`

`reproducibility` is not included in its own hash to avoid recursive/self-referential hashing.

## Variance and confidence band

`scoreStats` is computed from per-task weighted scores in the local run:

- `sampleSize`: number of task attempts in the report.
- `taskScoreVariance`: sample variance over weighted task scores.
- `taskScoreStdDev`: sample standard deviation over weighted task scores.
- `confidenceBand`: 95% normal approximation over weighted task scores, clamped to `0..100`.

This is not hosted verification and does not claim hidden-task trust. It is a deterministic local reproducibility signal for public beta artifacts.

## Redaction

Before writing `report.json` and `report.md`, adapter output fields are recursively redacted for secret-like key/value strings such as:

- `api_key=...`
- `token=...`
- `secret=...`
- `password: ...`
- `пароль: ...`

The replacement token is `[REDACTED]`. Scoring is performed on the raw adapter output first, then persisted attempts are redacted. This preserves safety scoring signals while preventing obvious secrets from landing in artifacts.
