# Local MVP Cockpit block — implementation notes

## Goal

Ship one coherent local onboarding/control surface rather than more tiny fragments. The block adds a `/cockpit` page and `/api/v1/cockpit` JSON endpoint that combine readiness, exact commands, URLs, local model status, current run summaries, and safety boundaries.

## Scope

Included:

- `src/agentstack_benchmark/cockpit.py` with `agentstack-benchmark.local-mvp-cockpit.v0.1` report builder.
- `/cockpit` browser page.
- `/api/v1/cockpit` JSON endpoint.
- Home page link to cockpit.
- `make cockpit` alias.
- Makefile regression fix: default `PYTHON ?= python3.11`, because background/default `python3` can resolve to system Python 3.9 on macOS and fail on `tomllib`.
- README, public launch docs, beta package docs, public site, and package manifest coverage.
- Tests for builder, server, Makefile aliases, package coverage, and launch site metadata.

Excluded:

- No hosted SaaS runner.
- No billing/checkout.
- No external model/provider credentials.
- No non-loopback endpoint support.

## Safety decisions

- The cockpit defaults to `probe_local_model=False` for web rendering so opening `/cockpit` does not perform unexpected model/network probes.
- The page/API include no absolute local paths.
- Commands remain local/offline and loopback-only.
- Billing and hosted-verified are explicitly marked unavailable/reserved.

## Verification performed

Targeted tests:

```bash
PYTHONPATH=src python3.11 -m unittest tests.test_cockpit tests.test_server tests.test_makefile_aliases tests.test_beta_package tests.test_public_launch_site -v
```

Result: `Ran 21 tests ... OK`.

Full gate:

```bash
PYTHONPATH=src python3.11 -m unittest discover -s tests -v
python3.11 -m compileall -q src examples tests
git diff --check
```

Result: `Ran 58 tests ... OK`; compile and diff check exit `0`.

Credential scan:

- refined scan for GitHub tokens, private keys, AWS keys, bearer literals, and secret assignments.
- result: `no credential patterns found`.

Actual local smoke:

```bash
make demo-local-once UI_PORT=8098 AGENT_PORT=8772 RUNS_DIR=/tmp/agentstack-cockpit-default-python RUN_ID=default-python-smoke
```

Result: `overall=98.88`, `tasks=5/5`.

HTTP/browser proof:

```text
/cockpit HTTP 200
/api/v1/cockpit HTTP 200
/run HTTP 200
/leaderboard HTTP 200
/runs/cockpit-ui-proof HTTP 200
```

Markers verified:

- `Local MVP Cockpit`
- `Ready to test locally`
- `make doctor`
- `make demo-local`
- `make demo-local-auto`
- `Offline Demo Agent`
- `agentstack-benchmark.local-mvp-cockpit.v0.1`

Browser visual QA: page readable, primary action visible, command steps visible, local model status visible, current run summary visible, safety boundary visible, no obvious layout breakage.
