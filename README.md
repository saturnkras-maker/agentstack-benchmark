# AgentStack Benchmark

Prototype “3DMark for AI agents”: a benchmark kernel for evaluating complete agent stacks, not only base models.

Current slice:

- local CLI runner;
- JSON agent manifest;
- JSON task pack;
- CLI adapter;
- local-only HTTP adapter prototype;
- local free-beta API preview (`healthz` + leaderboard);
- deterministic evaluator;
- JSON + Markdown reports;
- mock good/bad agents;
- 5-task MVP pack plus 20-task deterministic beta pack;
- unit tests proving score separation, local HTTP adapter behavior, API preview behavior, and beta task-pack coverage.

Run demo:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli run \
  --manifest examples/manifests/mock_good.json \
  --task-pack examples/task_packs/mvp_v0.json \
  --out artifacts/runs/demo-good

PYTHONPATH=src python3 -m agentstack_benchmark.cli run \
  --manifest examples/manifests/mock_good.json \
  --task-pack examples/task_packs/beta_v0_1.json \
  --out artifacts/runs/beta-good

PYTHONPATH=src python3 -m agentstack_benchmark.cli leaderboard \
  --runs-dir artifacts/runs \
  --out artifacts/leaderboard.json
```

HTTP adapter prototype:

`examples/manifests/mock_http.json` shows the local HTTP adapter contract. The runner POSTs each task as JSON to `adapter.endpoint` and expects a JSON object response such as:

```json
{"answer": "status: ready", "toolTrace": []}
```

For this prototype, endpoints are intentionally limited to `http://127.0.0.1`, `http://localhost`, or `http://[::1]` to avoid accidental external network side effects. Start a local agent server first, then run:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli run \
  --manifest examples/manifests/mock_http.json \
  --task-pack examples/task_packs/mvp_v0.json \
  --out artifacts/runs/demo-http
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Start local free-beta API preview:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli serve \
  --host 127.0.0.1 \
  --port 8088 \
  --runs-dir artifacts/runs
```

Preview endpoints:

- `GET /api/v1/healthz` — service health and current `pricingMode: free-beta`.
- `GET /api/v1/leaderboard` — JSON leaderboard from existing `report.json` run artifacts.

Monetization note: beta starts free. See `docs/monetization-v0.md` for the paid surfaces deferred until the benchmark proves trust and repeat usage.

Product/technical spec: `docs/product-technical-spec-v0.1.md`.
