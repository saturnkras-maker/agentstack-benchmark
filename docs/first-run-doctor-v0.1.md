# First-run doctor v0.1

The first-run doctor is a local readiness command for the touchable AgentStack Benchmark MVP.

It does not start servers, download models, call external endpoints, or require API keys. It prints JSON with exact next commands and URLs.

## Run

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli doctor
```

Fast non-probing mode:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli doctor --skip-local-model-probe
```

## What it reports

- `status: ready` when the local MVP can be started from the repository.
- `internetRequired: false` and `apiKeysRequired: false`.
- Python version and executable name.
- Whether expected docs/source paths exist.
- Whether the suggested UI and agent ports are free.
- Local model status from the loopback-only detector, unless probing is skipped.
- Exact local URLs:
  - UI home;
  - run form;
  - initial report;
  - leaderboard;
  - local agent endpoint.
- Exact next commands:
  - deterministic offline demo;
  - auto local model demo;
  - local model check;
  - one-shot smoke.

## Recommended usage

1. Run `doctor` first.
2. If `localModel.available` is false, run the deterministic offline demo.
3. If `localModel.available` is true, run `demo-local --agent-mode auto-local-model`.
4. Open the reported `urls.runForm`.

This command is intentionally informational. It does not create `hosted-verified` evidence and does not perform deploy/billing actions.
