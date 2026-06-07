# HTTP Adapter Contract v0.1

The local beta runner talks to HTTP agents through a small loopback-only JSON contract.
This is the preferred onboarding path for pilots because an agent only needs to expose one local `POST` handler.

## Safety boundary

- Runner accepts only `adapter.type: "http"` with loopback endpoints:
  - `http://127.0.0.1:...`
  - `http://localhost:...`
  - `http://[::1]:...`
- No external HTTP endpoint is allowed in the local beta runner.
- Expected answers, evaluator rubrics, budget fields, and depth keywords are not sent to the adapter.
- Adapter responses are treated as untrusted data and validated at the runner boundary.

Print the machine-readable contract:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli adapter-contract
```

## Manifest shape

```json
{
  "agentId": "my-local-agent",
  "name": "My Local Agent",
  "version": "0.1.0",
  "adapter": {
    "type": "http",
    "endpoint": "http://127.0.0.1:8765/tasks"
  },
  "limits": {
    "timeoutSecondsPerTask": 10,
    "maxRunsPerTask": 1
  }
}
```

## Request: runner → agent

`POST /tasks` with `Content-Type: application/json`.

```json
{
  "schemaVersion": "agentstack-benchmark.adapter.request.v0.1",
  "taskId": "t_context_extract",
  "category": "core",
  "prompt": "Answer from the provided context.",
  "context": {},
  "timeoutSeconds": 10
}
```

Required fields in canonical order:

1. `schemaVersion`
2. `taskId`
3. `category`
4. `prompt`
5. `context`
6. `timeoutSeconds`

Fields intentionally never sent:

- `expected`
- `budgetUsd`
- `depthKeywords`

## Response: agent → runner

Return a JSON object:

```json
{
  "schemaVersion": "agentstack-benchmark.adapter.response.v0.1",
  "answer": "status: ready",
  "toolTrace": ["file_read"],
  "costUsd": 0.001
}
```

Required fields:

- `answer`: string final answer.
- `toolTrace`: array of string evidence labels. Use `[]` if no tools were used.

Optional fields:

- `schemaVersion`: response schema marker.
- `costUsd`: numeric adapter-side cost estimate.

Invalid response shapes are converted into an adapter runtime error for the attempt.

## Minimal local handler

A stdlib example handler is available at `examples/agents/http_contract_agent.py`:

```bash
PYTHONPATH=src python3 examples/agents/http_contract_agent.py --host 127.0.0.1 --port 8765

PYTHONPATH=src python3 -m agentstack_benchmark.cli run \
  --manifest examples/manifests/mock_http.json \
  --task-pack examples/task_packs/mvp_v0.json \
  --out artifacts/runs/demo-http
```
