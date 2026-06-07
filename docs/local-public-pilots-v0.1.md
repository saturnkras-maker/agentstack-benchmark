# Local-public pilot ×5

This slice adds five **local fixture pilots** for calibrating the public beta package without crossing deploy, public-launch, billing, private-key, or arbitrary third-party-code boundaries.

## Why fixture pilots

The v2 path needs a credible five-agent calibration set, but real framework executions can require:

- third-party package installs;
- model/API credentials;
- participant-owned private keys or tool servers;
- arbitrary local/remote code execution outside the benchmark sandbox.

Those are not needed for this local-public beta slice. The fixture pilots prove the benchmark harness can run five distinct agent-stack entries, produce five reports, and build a track-aware leaderboard. Real SDK/agent execution remains a future participant/hosted verification concern.

## Selected pilot ecosystems

- **OpenAI Agents SDK**
  - Source: https://openai.github.io/openai-agents-python/
  - Rationale: first-party OpenAI agent framework; important for API-first hosted-agent builders.
  - Coverage: agent loop, tool calls, hosted/API-first workflows.

- **LangGraph**
  - Source: https://docs.langchain.com/oss/python/langgraph/overview
  - Rationale: graph/state-machine orchestration is relevant for durable workflows, branching, and recovery.
  - Coverage: state graph, durable workflow, multi-step reasoning.

- **Microsoft AutoGen**
  - Source: https://microsoft.github.io/autogen/stable/
  - Rationale: Microsoft-backed multi-agent ecosystem for collaborative conversation/orchestration patterns.
  - Coverage: multi-agent coordination, conversation orchestration, tool use.

- **CrewAI**
  - Source: https://docs.crewai.com/
  - Rationale: popular role/crew/task framing for delegated agent workflows.
  - Coverage: role-based agents, task delegation, workflow orchestration.

- **Claude Code + MCP**
  - Sources:
    - https://docs.anthropic.com/en/docs/claude-code/overview
    - https://modelcontextprotocol.io/docs/getting-started/intro
  - Rationale: developer-agent workflows plus tool/server interoperability are central to complete agent stacks.
  - Coverage: developer agent, MCP tool servers, tool interoperability.

## Registry

The local pilot registry is:

```text
examples/pilots/local_public_v0_1.json
```

Registry invariants:

- `schemaVersion: agentstack-benchmark.pilot-registry.v0.1`
- `track: local-public`
- `localOnly: true`
- exactly five pilots
- each pilot uses `localPilotMode: fixture-adapter`
- each pilot has `requiresPrivateKeys: false`
- each pilot points to an example manifest under `examples/manifests/pilots/`

## Run all local pilots

Use the CLI helper:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli pilot-run \
  --registry examples/pilots/local_public_v0_1.json \
  --task-pack examples/task_packs/mvp_v0.json \
  --out-dir artifacts/runs/pilots-local-public-v0-1 \
  --leaderboard-out artifacts/pilot-leaderboard.json
```

Expected output shape:

```json
{"pilots": 5, "leaderboardEntries": 5, "outDir": "...", "leaderboardOut": "..."}
```

Artifacts:

- one `report.json` + `report.md` under each `artifacts/runs/pilots-local-public-v0-1/<pilotId>/` directory;
- `artifacts/pilot-leaderboard.json`;
- `artifacts/pilot-leaderboard.md`.

## Boundary language

These pilot fixtures are not claims that the real SDK/framework was executed. Each registry entry contains a `realExecutionBoundary` string that says real execution is outside this local fixture because it may require package installs, participant-owned model credentials, local tools, or MCP servers.

This keeps the beta trust foundation honest: local-public pilots are reproducible harness calibration, not hosted verified results.
