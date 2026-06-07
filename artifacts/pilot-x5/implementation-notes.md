# Pilot ×5 slice

## Scope

Autonomous v2 mode active. This slice implements the next critical-path item after reproducibility/redaction: pilot ×5.

In scope:

- choose 5 credible agent/framework ecosystems for local-public beta calibration;
- record source-backed selection rationale;
- add a local-only pilot registry;
- add five safe local fixture manifests that can generate benchmark reports without API keys, private keys, hosted infra, external deploy, public launch, billing, or arbitrary remote code execution;
- add a helper/CLI path to run all local pilots into report artifacts;
- verify five local pilot reports and a leaderboard from those reports.

Out of scope / safety boundaries:

- no actual third-party SDK install or execution;
- no model/API/private-key flows;
- no hosted verified status;
- no hidden tasks;
- no auth/rate limit;
- no external deploy or public launch.

## Preflight

- `git status --short --branch && git log --oneline -5`: repo clean on `main`; latest commit `33ab1a8 feat: add report reproducibility metadata`.
- Inspected current CLI, runner, task packs, examples/manifests, leaderboard and tests.
- Official-source availability check for selected ecosystems:
  - `200 https://openai.github.io/openai-agents-python/ :: OpenAI Agents SDK`
  - `200 https://docs.langchain.com/oss/python/langgraph/overview :: LangGraph overview - Docs by LangChain`
  - `200 https://microsoft.github.io/autogen/stable/ :: AutoGen — AutoGen`
  - `200 https://docs.crewai.com/ :: CrewAI Documentation - CrewAI`
  - `200 https://modelcontextprotocol.io/docs/getting-started/intro :: What is the Model Context Protocol (MCP)? - Model Context Protocol`
  - `200 https://docs.anthropic.com/en/docs/claude-code/overview :: Overview - Claude Code Docs`

## Pilot set decision

Selected five local-public pilot targets:

1. OpenAI Agents SDK — first-party OpenAI agent framework; direct relevance for hosted/API-first builders.
2. LangGraph — graph/state-machine agent orchestration; strong coverage for durable workflows.
3. Microsoft AutoGen — multi-agent conversation/orchestration ecosystem; covers collaborative agent teams.
4. CrewAI — role/crew/task agent orchestration; covers popular role-based workflow framing.
5. Claude Code + MCP — developer-agent + tool protocol ecosystem; covers tool/server integration and MCP-style interoperability.

Decision: do **local fixture pilots** now, not real SDK executions. Reason: real executions would likely require package installs, API keys, model credentials, or arbitrary third-party code; v2 public beta trust path needs a reproducible local harness first.

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_pilots.PilotRegistryTests.test_local_public_pilot_registry_selects_five_credible_frameworks -v`
  - expected failure: `ModuleNotFoundError: No module named 'agentstack_benchmark.pilots'`.

## GREEN / verification

Implementation:

- added `src/agentstack_benchmark/pilots.py` with registry validation and `run_local_pilots(...)`;
- added `agentstack-benchmark pilot-run` CLI command;
- added `examples/pilots/local_public_v0_1.json` registry with five source-backed local-public pilots;
- added five safe fixture manifests under `examples/manifests/pilots/`;
- added `examples/agents/pilot_fixture_agent.py` to reuse deterministic mock answers while tagging each pilot profile;
- documented the fixture boundary in `docs/local-public-pilots-v0.1.md` and README.

Implementation correction during GREEN:

- first `tests.test_pilots` run found local fixture manifests used `examples/agents/pilot_fixture_agent.py`, but CLI adapters run with `cwd=examples`, so the command path resolved incorrectly and reports scored `24.94`.
- fixed manifests to use `agents/pilot_fixture_agent.py`, preserving the existing runner project-root behavior.

Targeted GREEN:

- `PYTHONPATH=src python3 -m unittest tests.test_pilots -v`
  - result: `Ran 3 tests in 1.139s` / `OK`.

Full/compile gate:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 29 tests in 9.737s` / `OK`; compile gate exit `0`.

Manual pilot smoke:

- `PYTHONPATH=src python3 -m agentstack_benchmark.cli pilot-run --registry examples/pilots/local_public_v0_1.json --task-pack examples/task_packs/mvp_v0.json --out-dir /tmp/agentstack-pilot-smoke/runs --leaderboard-out /tmp/agentstack-pilot-smoke/leaderboard.json`
  - output: `{"pilots": 5, "leaderboardEntries": 5, "outDir": "/tmp/agentstack-pilot-smoke/runs", "leaderboardOut": "/tmp/agentstack-pilot-smoke/leaderboard.json"}`
  - assertions:
    - `pilot_reports=5`
    - `leaderboard_entries=5`
    - `tracks=['local-public']`
    - `agent_ids=['pilot-autogen', 'pilot-claude-mcp', 'pilot-crewai', 'pilot-langgraph', 'pilot-openai-agents-sdk']`
    - `tasks_total=[5]`

Completion state before commit:

- pending: clean temp smoke artifacts, diff check, atomic commit.
