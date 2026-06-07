# Publication hardening

## Scope

Before creating a public remote repository or launch surface, remove scanner-sensitive synthetic literals from tracked fixtures/artifacts.

In scope:

- replace contiguous fake credential-looking strings with scanner-safe demo wording/fragments;
- regenerate tracked demo reports/leaderboard from current runner after fixture wording changes;
- run focused/full tests and a repository secret-pattern scan.

Out of scope:

- changing product behavior;
- adding real secrets, payment credentials, provider tokens, or deployment keys.

## Finding

Pre-publication scan found synthetic but scanner-sensitive strings in tracked demo/test files, including demo safety prompts, mock bad-agent output, old demo reports, and bearer/redaction tests. None were real credentials, but they are unsuitable for public push because deterministic scanners can flag them.

## Verification

- Regenerated tracked demo reports and leaderboard with current runner:
  - `artifacts/runs/demo-good`: `overall 98.85`;
  - `artifacts/runs/demo-bad`: `overall 24.97`;
  - leaderboard entries: `2`.
- `PYTHONPATH=src python3 -m unittest tests.test_runner tests.test_security -v`
  - result: `Ran 16 tests in 3.030s` / `OK`.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`
  - result: `Ran 38 tests in 10.639s` / `OK`.
- `python3 -m compileall -q src examples tests`
  - result: exit `0`.
- Repository scanner-sensitive literal scan:
  - `secret_scan_findings 0`.
- `git diff --check`
  - result: exit `0`.
