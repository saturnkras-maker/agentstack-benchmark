# Local MVP Cockpit v0.1

The Local MVP Cockpit is the guided local onboarding surface for AgentStack Benchmark.

It combines first-run readiness, exact commands, browser URLs, local model status, current run summaries, and safety boundaries in one page.

## Start

```bash
make doctor
make demo-local
```

Then open:

- `http://127.0.0.1:8088/cockpit`
- `http://127.0.0.1:8088/run`
- `http://127.0.0.1:8088/leaderboard`

The run form can use the offline demo agent endpoint:

```text
http://127.0.0.1:8765/tasks
```

## Cockpit command

If you already have run artifacts and only want to serve the UI:

```bash
make cockpit
```

Equivalent explicit Python command:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli serve \
  --host 127.0.0.1 \
  --port 8088 \
  --runs-dir artifacts/runs
```

## JSON API

```text
GET http://127.0.0.1:8088/api/v1/cockpit
```

The API returns:

- `schemaVersion`: `agentstack-benchmark.local-mvp-cockpit.v0.1`
- readiness and launch boundary flags;
- exact `make` commands;
- `/cockpit`, `/run`, `/leaderboard`, report, and agent endpoint URLs;
- local model status;
- current local run count and leader;
- recent local runs for quick navigation.

## Local model path

Optional local model check:

```bash
make local-model-check
make demo-local-auto
```

If no loopback local model backend is available, the deterministic offline demo remains the fallback. The cockpit page does not require internet, API keys, hosted services, model downloads, or payment configuration.

## Safety boundary

- No internet required for the offline demo.
- No API keys required.
- No billing checkout connected.
- No hosted verified runner included.
- No credential material embedded in docs, site, or generated package manifests.
- `/run` and local model adapter paths remain loopback-only.

## Verification

```bash
PYTHONPATH=src python3 -m unittest tests.test_cockpit tests.test_server -v
make demo-local-once
```
