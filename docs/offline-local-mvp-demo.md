# Offline local MVP demo

This is the fastest path to touch the AgentStack Benchmark UX locally without internet, API keys, hosted services, or a downloaded model file.

It starts a deterministic offline demo agent that implements the HTTP adapter contract on loopback, runs the MVP task pack once, and serves the visual UI/leaderboard from local `report.json` artifacts.

## One-command path

From the repository root:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local
```

Default local URLs:

- UI home: `http://127.0.0.1:8088/`
- Run form: `http://127.0.0.1:8088/run`
- Initial report: `http://127.0.0.1:8088/runs/offline-demo-run`
- Leaderboard: `http://127.0.0.1:8088/leaderboard`
- Offline demo agent endpoint: `http://127.0.0.1:8765/tasks`

## Smoke test without starting the long-lived UI

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local --once
```

Expected JSON includes:

- `mode: offline-local-demo`
- `internetRequired: false`
- `apiKeysRequired: false`
- `overall` above `90`
- `reportUrl` pointing at the local UI route for the generated run

## Browser path

1. Start the demo:

   ```bash
   PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local
   ```

2. Open `http://127.0.0.1:8088/run`.
3. Use endpoint `http://127.0.0.1:8765/tasks`.
4. Click **Run benchmark**.
5. Open the generated report and leaderboard.

## What this is and is not

This is a local/offline MVP demo. It is intentionally deterministic so that the product UX is testable without internet or credentials.

It can also try a real local model backend if one is already running on loopback:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check

PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local \
  --agent-mode auto-local-model
```

`auto-local-model` uses a detected OpenAI-compatible or Ollama loopback endpoint when available, and otherwise falls back to this deterministic offline demo without hanging. See `docs/local-model-adapter-v0.1.md`.
