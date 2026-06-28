# AgentStack Benchmark — Product + Technical Spec v0.1

Дата: 2026-06-07 02:21 +07
Owner/integrator: Hermes
Reviewer/co-executor requested: Raskovalobot

## 1. Product thesis

AgentStack Benchmark is a public benchmark service for **complete AI agent systems**, not only base LLMs.

The service evaluates an agent as an engineering construction:

- model/provider;
- system prompt and policies;
- memory;
- skills/plugins/tools/MCP;
- browser/terminal/API/file abilities;
- routing and orchestration;
- speed, cost, reliability;
- safety and prompt-injection resistance;
- reproducibility and traceability.

Short positioning:

> 3DMark for AI agents: a reproducible scorecard for the full agent stack.

## 2. Why this is not just another leaderboard

Existing leaderboards validate demand but are fragmented by task family:

- HAL / Princeton — holistic, cost-aware agent leaderboard: https://hal.cs.princeton.edu/
- Open Agent Leaderboard / IBM + Hugging Face: https://huggingface.co/blog/ibm-research/open-agent-leaderboard
- Steel.dev — browser/coding/computer-use leaderboard aggregation: https://leaderboard.steel.dev/
- The Agentic Leaderboard — open-source agent rankings: https://theagenticleaderboard.com/
- Agent Arena — run/rate LLM agents: https://www.agent-arena.com/leaderboard
- ClawBench — live AI agent rankings: https://www.clawbench.com/leaderboard
- Galileo Agent Leaderboard: https://galileo.ai/agent-leaderboard
- Artificial Analysis coding agents: https://artificialanalysis.ai/agents/coding-agents
- Terminal-Bench: https://www.tbench.ai/leaderboard
- SWE-bench: https://www.swebench.com/
- WebArena: https://webarena.dev/
- OSWorld: https://os-world.github.io/
- BFCL function calling: https://huggingface.co/spaces/gorilla-llm/berkeley-function-calling-leaderboard
- Foundry browser-agent benchmark platform: https://www.thefoundryai.com/leaderboard
- AgentBench: https://github.com/THUDM/AgentBench

Whitespace: a consumer/community-friendly service where a user can submit **their own complete agent stack**, run a standard benchmark, get public score + private trace/deep report, and learn **which architectural decisions caused the result**.

## 3. MVP scope

MVP is not a global scientific standard yet. MVP proves one vertical slice:

1. User/maintainer defines an agent manifest.
2. Runner executes a small task pack against an adapter.
3. System records attempts, timing, stdout/stderr, normalized answers, and task verdicts.
4. Evaluator computes a scorecard.
5. Report is saved as JSON + Markdown.
6. Leaderboard can sort runs by overall score and sub-scores.

MVP can start local/CLI-first, then become web service.

## 4. Scorecard v0.1

### 4.1 Dimensions

- **Quality** — task correctness against deterministic or judge-based rubric.
- **Depth** — evidence use, self-checking, handling of ambiguity, no shallow answer when deeper work is required.
- **Speed** — wall-clock execution time normalized by task class.
- **Cost efficiency** — token/API/tool/compute cost per successful task. MVP can use declared or estimated cost if exact telemetry is unavailable.
- **Reliability** — variance across repeated runs; stable pass rate.
- **Autonomy** — number of required human interventions; lower is better.
- **Tool-use** — correct and necessary use of browser/files/terminal/API/MCP rather than hallucinated tool claims.
- **Memory/skills** — ability to use provided memory/skills and transfer information between tasks or sessions.
- **Safety** — prompt-injection resistance, secret handling, refusal of unsafe requests.
- **Reproducibility** — ability to rerun under same manifest, task pack, adapter, sandbox, and budget.

### 4.2 Overall score

Initial formula:

```text
overall =
  0.30 * quality +
  0.15 * reliability +
  0.12 * tool_use +
  0.10 * safety +
  0.10 * speed +
  0.08 * cost_efficiency +
  0.07 * depth +
  0.05 * memory_skills +
  0.03 * autonomy
```

Do not hide sub-scores. A single number is marketing; the profile is the product value.

### 4.3 Task verdict levels

- `PASS` — meets objective and constraints.
- `PARTIAL` — useful but incomplete or minor constraint miss.
- `FAIL` — wrong, missing, unsafe, or non-executable.
- `INVALID_RUN` — adapter/runtime failed, timeout, malformed output.

## 5. MVP task packs

Start with synthetic, deterministic tasks before expensive real-world tasks.

### Pack A — Core reliability

1. Exact instruction following.
2. Context extraction.
3. Multi-step file reasoning.
4. Simple coding/patch suggestion without external side effects.
5. Output schema compliance.

### Pack B — Tool-use / environment

1. Read local file and answer from it.
2. Use terminal command and summarize actual output.
3. Use provided API/mock endpoint.
4. Browser/research task later.

### Pack C — Safety

1. Prompt-injection string inside a document.
2. Secret-exfiltration bait.
3. Tool misuse request.
4. Dangerous command refusal.

### Pack D — Memory/skills

1. Use provided memory fact correctly.
2. Preserve state across two subtasks.
3. Apply a provided skill/rule to solve a task.

### Pack E — Speed/cost

1. Same task under strict time budget.
2. Same task with minimal tools.
3. Repeated run stability.

## 6. Anti-cheat and contamination

MVP guardrails:

- versioned task packs;
- public sample tasks + hidden evaluation tasks;
- budget/time limits per task;
- repeated runs;
- deterministic seeds where possible;
- trace logs and adapter transcript capture;
- no self-reported scores without runner artifact;
- manifest hash + task pack hash + runner version hash in every report;
- disclose model/provider/tool access;
- store raw run artifacts privately by default, publish only safe summaries.

Later:

- private hidden task pool;
- Docker sandbox;
- network policy tiers;
- external judge ensemble for non-deterministic tasks;
- anomaly detection for suspiciously memorized answers;
- reproducibility badges.

## 7. Agent manifest v0.1

```json
{
  "agentId": "mock-good-agent",
  "name": "Mock Good Agent",
  "version": "0.1.0",
  "adapter": {
    "type": "cli",
    "command": "python3 examples/agents/mock_good_agent.py"
  },
  "model": {
    "provider": "mock",
    "name": "deterministic-demo"
  },
  "capabilities": {
    "browser": false,
    "terminal": false,
    "files": false,
    "memory": false,
    "skills": false,
    "mcp": false
  },
  "limits": {
    "timeoutSecondsPerTask": 10,
    "maxRunsPerTask": 1
  }
}
```

## 8. Technical architecture

### 8.1 Local MVP vertical slice

- Python standard-library runner.
- CLI adapter first.
- JSON task pack.
- JSON/Markdown run report.
- Unit tests.

This is enough to prove the benchmark kernel before web/UI complexity.

### 8.2 Web MVP architecture

- Backend: FastAPI or equivalent Python API.
- DB: PostgreSQL for production; SQLite acceptable for local prototype.
- Queue: Redis/RQ, Dramatiq, Celery, or lightweight worker queue.
- Runner: isolated worker process; Docker sandbox when accepting third-party code.
- Storage: local/S3-compatible object storage for traces and reports.
- Frontend: Next.js or simple server-rendered UI initially.
- Auth: GitHub/OAuth/email magic link later.
- Payments: keep out of MVP; add paid reports after product value is proven.

### 8.3 Core services

- `api-service` — manifests, submissions, leaderboard, reports.
- `runner-service` — executes tasks via adapter.
- `evaluator-service` — computes verdicts/scores.
- `trace-service` — stores transcripts/logs/artifacts.
- `report-service` — creates human-readable breakdown.
- `leaderboard-service` — public rankings and filters.

### 8.4 Data model outline

- `agents` — owner, name, public metadata.
- `agent_versions` — manifest, manifest_hash, version.
- `task_packs` — name, version, public/hidden flags, hash.
- `tasks` — prompt, evaluator type, expected/rubric, category.
- `benchmark_runs` — agent_version_id, task_pack_id, status, total_score, costs, started/finished.
- `task_attempts` — run_id, task_id, attempt_no, stdout/stderr, normalized_output, timing, verdict, sub_scores.
- `traces` — safe artifact references, redaction status.
- `reports` — public summary and private deep report.
- `leaderboard_snapshots` — cached rankings by category/version.

## 9. API outline

Initial REST shape:

- `POST /api/agents` — create agent.
- `POST /api/agent-versions` — upload manifest.
- `GET /api/task-packs` — list public packs.
- `POST /api/runs` — enqueue benchmark run.
- `GET /api/runs/{runId}` — run status/result.
- `GET /api/leaderboard` — paginated rankings.
- `GET /api/agents/{agentId}` — public agent page.
- `GET /api/runs/{runId}/report` — public or private report depending on auth.

Consistent error body:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid manifest",
    "details": {}
  }
}
```

## 10. Frontend MVP pages

1. Landing: “Benchmark your AI agent stack”.
2. Leaderboard: overall + filters by category.
3. Agent page: manifest summary, versions, runs, badges.
4. Run report: scorecard, task breakdown, traces available/not available.
5. Compare: two agents side-by-side.
6. Submit docs: manifest and adapter examples.

## 11. Monetization hypotheses

Current beta decision: **free first**. The first launch should optimize for trust, submissions, and repeat usage, not payment capture.

Free beta:

- public basic run;
- public leaderboard;
- short report;
- badge;
- safe reproducibility/trace metadata where publishable.

Paid later:

- private benchmark runs;
- deep trace breakdown;
- recommendations to improve score;
- compare with competitors;
- historical tracking;
- API access;
- team dashboard;
- verified/reproducible badge;
- custom task packs.

Crypto:

- not in MVP;
- use a gateway later, not agent-managed private keys;
- no seed/private-key handling by agents.

## 12. Roadmap

### Week 1 — Benchmark kernel

- Local CLI runner.
- Manifest schema.
- Task pack schema.
- Deterministic evaluator.
- JSON + Markdown report.
- Good/bad mock agents.
- Unit tests.

### Week 2 — First web preview

- Minimal API around runner.
- SQLite DB.
- Static leaderboard from local runs.
- Landing and report page.

### Week 3 — Real adapters

- HTTP adapter.
- Docker adapter design.
- Timeout/resource controls.
- Trace redaction.

### Week 4 — Public beta prep

- 20-30 tasks.
- Submission docs.
- GitHub repo/landing copy.
- First known agents tested manually.
- Community post draft.

### Weeks 5-6 — Trust layer

- Hidden tasks.
- Repeat runs.
- Reproducibility badge.
- Paid deep report prototype.

## 13. Immediate implementation slice

Build a local runnable prototype:

- `agentstack-benchmark run --manifest examples/manifests/mock_good.json --task-pack examples/task_packs/mvp_v0.json --out artifacts/runs/demo-good`
- produces `report.json` and `report.md`;
- unit test proves good agent scores higher than bad agent;
- no network, no external sends, no payments.

This slice proves the kernel before UI/payment complexity.

## 14. Current coordination state

- Raskovalobot consult packet created: `/home/user/.openclaw/workspace/projects/agentstack-benchmark/task-packets/raskovalobot-consult-2026-06-07.md`
- Telegram visible handoff sent to topic 4269, message id `22328`.
- Agent relay event delivered/spooled: `030bf5cb9f4f9543efee94cb8d8b844247a021061c29b8185610a61eb47a50d9`.
- Subagent CLI/delegate attempts failed with provider `Broken pipe`; parent Hermes continues implementation and will integrate Raskovalobot feedback when it arrives.

## 15. Open questions for v0.2

- Product name: AgentStack Benchmark, AgentMark, Agent3DMark, AgentBench Arena, or another brand?
- Open source boundary: runner open, evaluator open, hidden tasks private?
- Which first real agents to test publicly?
- Should the first beta require Docker submission or start with HTTP/CLI adapters?
- Which category should be flagship: coding, research, computer-use, or “full-stack mixed pack”?
