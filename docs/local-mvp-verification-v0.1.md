# Local MVP verification v0.1

`make verify-local-mvp` is the one-command proof loop for the local-public beta.

It is designed for a pre-manual-test check: run it from the repository root and verify that the offline demo can produce a report and that the browser/API surfaces are reachable.

```bash
make verify-local-mvp
```

Equivalent explicit command:

```bash
PYTHONPATH=src python3.11 -m agentstack_benchmark.cli verify-local-mvp \
  --out-dir artifacts/local-mvp-verification
```

## What it checks

- Starts the deterministic offline demo agent on loopback.
- Runs one local-public benchmark report.
- Starts the local preview UI on loopback.
- Fetches and validates:
  - `/api/v1/healthz`
  - `/cockpit`
  - `/api/v1/cockpit`
  - `/run`
  - `/leaderboard`
  - `/runs/<runId>`
- Confirms the expected demo score: `98.88`, `5/5` tasks.
- Writes proof artifacts:
  - `artifacts/local-mvp-verification/local_mvp_verification.json`
  - `artifacts/local-mvp-verification/local_mvp_verification.md`

## Boundary

This command is local-only:

- no internet required;
- no API keys required;
- no hosted runner;
- no billing or checkout;
- no hidden task corpus;
- no production credentials.

Use this before manual browser testing. If it returns `pass`, open the product cockpit with:

```bash
make demo-local
# then open http://127.0.0.1:8088/cockpit
```
