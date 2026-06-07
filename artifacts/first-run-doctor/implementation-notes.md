# First-run doctor slice — implementation notes

## Goal

Avoid first-run friction for the touchable local/offline MVP. Users should have one command that prints readiness, exact commands, local URLs, port status, and local model status without starting servers or requiring internet/API keys.

## Implemented

- `src/agentstack_benchmark/doctor.py`:
  - builds a JSON readiness report;
  - checks suggested UI/agent port availability;
  - reports local model status or supports skipped probe;
  - returns exact local URLs and commands.
- CLI:
  - `doctor` command;
  - `--skip-local-model-probe` for instant non-probing checks;
  - host/port/model probe options.
- Docs/surfaces:
  - `docs/first-run-doctor-v0.1.md`;
  - README/public beta package/public launch/site metadata updates.

## Safety boundaries

- Does not start servers.
- Does not download models.
- Does not require internet.
- Does not require or print API keys/secrets.
- Does not perform deploy/billing/live send actions.

## Proof before PR

- Targeted doctor/package/site tests: OK.
- Full test suite: `Ran 54 tests in 16.021s` / `OK`.
- Compile: `python3.11 -m compileall -q src examples tests` exit `0`.
- `doctor --skip-local-model-probe`: JSON status `ready`, `doesNotStartServers=true`, `recommendedMode=offline`.
- `doctor`: local model unavailable on this Mac, reason `no-loopback-local-model-backend-detected`, no internet/API keys required.
- `git diff --check`: exit `0`.
- Changed diff secret scan: `[]`.
