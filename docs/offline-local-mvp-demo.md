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

It is not yet a true local LLM backend. The next backend slice can add an optional `llama.cpp`/GGUF adapter when a local `llama-server`, `llama-cli`, or `.gguf` model is available on the machine. The product UX will remain the same: an HTTP adapter endpoint is benchmarked and shown in the same report UI.
