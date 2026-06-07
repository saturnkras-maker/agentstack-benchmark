# Public launch v0.1

This document records the public launch surface for AgentStack Benchmark.

## Launch target

- Repository: `https://github.com/saturnkras-maker/agentstack-benchmark`
- Release branch: `main`
- Static launch page source: `site/`
- Deployment target: GitHub Pages via `gh-pages` branch.

## Current MVP surface

The current product MVP is a local/offline browser experience:

1. Run a one-command local demo:

   ```bash
   PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local
   ```

2. Open the local run form: `http://127.0.0.1:8088/run`.
3. Use the demo loopback adapter endpoint: `http://127.0.0.1:8765/tasks`.
4. Click **Run benchmark**.
5. Inspect the generated report and leaderboard.

This path requires no internet, no API keys, no hosted service, and no downloaded model file. The built-in demo agent is deterministic by design so the UX/UI can be tested immediately.

If a real local model backend is already running on loopback, the same UX can use it instead:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check

PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local \
  --agent-mode auto-local-model
```

`auto-local-model` supports loopback OpenAI-compatible and Ollama endpoints, rejects external URLs, and falls back to the deterministic offline demo instead of hanging when no backend is available.

## Guarantees

- No direct push to `main`.
- Public beta code reaches `main` through PR merge gates.
- Launch page contains no production secrets, API keys, private model credentials, private keys, or payment credentials.
- `local-public` is the default track.
- `hosted-verified` remains reserved for a future server-side runner.
- Offline demo is explicitly `local-public`, not `hosted-verified`.

## Public beta commands

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local --once

PYTHONPATH=src python3 -m agentstack_benchmark.cli beta-package \
  --out-dir artifacts/public-beta-package
```

## Non-goals for this launch

- No hidden task corpus.
- No hosted runner execution.
- No paid checkout until a billing provider and legal/payment workflow are configured.
