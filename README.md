# AgentStack Benchmark

Prototype “3DMark for AI agents”: a benchmark kernel for evaluating complete agent stacks, not only base models.

Current slice:

- local CLI runner;
- JSON agent manifest;
- JSON task pack;
- CLI adapter;
- local-only HTTP adapter prototype;
- deterministic evaluator;
- JSON + Markdown reports;
- mock good/bad agents;
- unit tests proving score separation and local HTTP adapter behavior.

Run demo:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli run \
  --manifest examples/manifests/mock_good.json \
  --task-pack examples/task_packs/mvp_v0.json \
  --out artifacts/runs/demo-good

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

Product/technical spec: `docs/product-technical-spec-v0.1.md`.
