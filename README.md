# AgentStack Benchmark

Prototype “3DMark for AI agents”: a benchmark kernel for evaluating complete agent stacks, not only base models.

Current slice:

- local CLI runner;
- JSON agent manifest;
- JSON task pack;
- CLI adapter;
- local-only HTTP adapter prototype;
- versioned HTTP adapter contract (`docs/adapter-contract-v0.1.md` + `adapter-contract` CLI);
- local free-beta API preview (`healthz` + leaderboard);
- local public-beta web preview (`/`, `/leaderboard`, `/runs/{runId}`);
- run-level `track` field (`local-public` today; `hosted-verified` reserved for later server-side verified runs);
- deterministic evaluator with frozen `scoring_schema_v1` (`docs/scoring-schema-v1.md`);
- JSON + richer Markdown reports with track/schema/scorecard/task-score context;
- reproducibility/redaction metadata (`docs/reproducibility-redaction.md`);
- mock good/bad agents;
- 5-task MVP pack plus 20-task deterministic beta pack;
- unit tests proving score separation, local HTTP adapter behavior, API/web preview behavior, and beta task-pack coverage.

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

HTTP adapter contract:

`docs/adapter-contract-v0.1.md` defines the versioned local HTTP adapter contract. Print the machine-readable contract with:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli adapter-contract
```

`examples/manifests/mock_http.json` shows the manifest shape. The runner POSTs each task as JSON to `adapter.endpoint` and expects a JSON object response such as:

```json
{"schemaVersion": "agentstack-benchmark.adapter.response.v0.1", "answer": "status: ready", "toolTrace": []}
```

For this prototype, endpoints are intentionally limited to `http://127.0.0.1`, `http://localhost`, or `http://[::1]` to avoid accidental external network side effects. Start the example local HTTP handler first, then run:

```bash
PYTHONPATH=src python3 examples/agents/http_contract_agent.py --host 127.0.0.1 --port 8765

PYTHONPATH=src python3 -m agentstack_benchmark.cli run \
  --manifest examples/manifests/mock_http.json \
  --task-pack examples/task_packs/mvp_v0.json \
  --out artifacts/runs/demo-http
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Start local free-beta API + web preview:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli serve \
  --host 127.0.0.1 \
  --port 8088 \
  --runs-dir artifacts/runs
```

Preview web pages:

- `GET /` — local public-beta landing page with health/runs/leaderboard navigation.
- `GET /leaderboard` — HTML leaderboard from existing local `report.json` run artifacts.
- `GET /runs/{runId}` — HTML run report summary for a safe single-segment `runId`, including a track badge.

Preview JSON endpoints:

- `GET /api/v1/healthz` — service health and current `pricingMode: free-beta`.
- `GET /api/v1/leaderboard` — JSON leaderboard entries from existing `report.json` run artifacts, each with a separate `track` field.
- `GET /api/v1/runs` — deterministic summaries for existing local run artifacts, each with `track: local-public`.
- `GET /api/v1/runs/{runId}/report` — one full run report by safe single-segment `runId`, with wrapper/report `track` fields.

Track values are intentionally enum-like and closed for the beta foundation: `local-public` is the only default assigned by local runs; `hosted-verified` is reserved for a future server-side hosted verified runner and is never assigned automatically by the local preview.

Reports embed `scoringSchema.schemaVersion: scoring_schema_v1` next to the run-level track. The schema freezes the current deterministic weights and verdict vocabulary for the local-public beta; LLM-as-judge, hidden tasks, and hosted verification stay outside this scoring slice.

Reports also embed `reproducibility.artifactHash` (SHA-256 over canonical fields including `track`), local score variance/confidence-band metadata, and redaction stats. Secret-like adapter output is replaced with `[REDACTED]` before `report.json` / `report.md` are persisted.

Monetization note: beta starts free. See `docs/monetization-v0.md` for the paid surfaces deferred until the benchmark proves trust and repeat usage.

Product/technical spec: `docs/product-technical-spec-v0.1.md`.
