# Hosted UX runner v0.1

This is the first repo-local/no-deploy slice of the hosted benchmark experience.
It gives a user a browser flow for connecting a local HTTP agent, running the MVP task pack, and opening a visual score report.

## Current scope

Included:

- `GET /run` browser form.
- `POST /run` browser-triggered benchmark run.
- Visual completion page with report/leaderboard links.
- Persisted run artifacts under the configured `--runs-dir`.
- Loopback-only HTTP adapter endpoints: `127.0.0.1`, `localhost`, or `::1`.

Not included yet:

- public hosted execution;
- external internet agent endpoints;
- API key or secret storage;
- user accounts;
- async job queue;
- payment or hosted-verified track assignment.

## Why loopback-only in this slice

The runner can execute prompts against an agent endpoint. In a real hosted service this requires authentication, abuse controls, secret handling, queue isolation, rate limits, and egress policy. This first UX slice keeps the experience testable without introducing those risks.

## 1. Start an example HTTP agent

In one terminal:

```bash
PYTHONPATH=src python3 examples/agents/http_contract_agent.py \
  --host 127.0.0.1 \
  --port 8765
```

The endpoint will be:

```text
http://127.0.0.1:8765/tasks
```

A real agent should implement the same adapter contract documented in `docs/adapter-contract-v0.1.md`.

## 2. Start the preview server

In another terminal:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli serve \
  --host 127.0.0.1 \
  --port 8088 \
  --runs-dir artifacts/runs
```

## 3. Open the UX

Open:

```text
http://127.0.0.1:8088/run
```

Fill in:

- Agent ID: safe identifier, for example `my-local-agent`.
- Agent name: display name.
- Version: for example `0.1.0`.
- HTTP endpoint: `http://127.0.0.1:8765/tasks`.
- Run ID: optional safe identifier; if empty, one is generated.

Click **Run benchmark**.

## 4. Read the result visually

After a successful run, the completion page links to:

- visual report: `/runs/{runId}`;
- leaderboard: `/leaderboard`;
- JSON report: `/api/v1/runs/{runId}/report`.

The report shows:

- overall score;
- passed/total tasks;
- track badge (`local-public`);
- dimension scores: reliability, quality, speed, cost efficiency, tool use, safety, depth, memory/skills, and autonomy.

## Adapter response contract

For each task, the local agent receives a JSON request and returns a JSON object:

```json
{
  "schemaVersion": "agentstack-benchmark.adapter.response.v0.1",
  "answer": "final answer here",
  "toolTrace": ["tool_or_evidence_label"],
  "costUsd": 0.001
}
```

Required fields:

- `answer`: string final answer.
- `toolTrace`: string array; use `[]` when no tools were used.

## Next hosted slice

The next product layer should add an authenticated job submission API and queued runner boundary before enabling external endpoints or API-key handling.
