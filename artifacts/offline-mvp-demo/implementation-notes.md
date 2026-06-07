# Offline MVP demo slice — implementation notes

## Goal

Ship the smallest local/offline MVP path so a user can clone the repo, stay offline, start a local demo agent/UI, run the benchmark, and inspect a visual score report.

## Acceptance criteria

- No internet, API keys, hosted services, npm, or external model download required.
- A deterministic offline demo agent is included in the repo and serves the HTTP adapter contract locally.
- A one-command CLI starts the offline demo agent and preview UI, optionally runs one demo benchmark, and prints exact local URLs.
- Generated report is `track: local-public` with overall score > 90 and 5/5 MVP tasks passed.
- CLI output exposes local URLs for UI, `/run`, report, and leaderboard.
- README/docs explain that this is a deterministic offline demo, not a real hosted runner or paid model.
- Public launch surface points to the one-command offline MVP demo and no longer presents the old PR #1 link as the current launch gate.

## Scope boundary

- This is an offline MVP/product demo, not a production hosted runner.
- True GGUF/llama.cpp support is a follow-up backend once a local model binary/runtime exists.
- The demo agent is deterministic by design so that UX/UI can be tested immediately without network/model setup.
- It remains `local-public`, not `hosted-verified`.

## Implementation summary

- Added `agentstack_benchmark.offline_demo` with a deterministic loopback HTTP demo agent.
- Added CLI command `demo-local`:
  - `demo-local --once` runs a non-blocking smoke/proof and exits.
  - `demo-local` runs an initial benchmark, starts the offline demo agent, and serves UI/leaderboard.
- Added `examples/manifests/offline_demo.json`.
- Added docs: `docs/offline-local-mvp-demo.md`.
- Updated README quick start and public beta package manifest/checklist.
- Updated `site/index.html`, `site/launch.json`, and `docs/public-launch-v0.1.md` to advertise the touchable offline MVP.

## Proof

- Targeted offline demo tests: `tests.test_offline_demo` — 4 tests OK.
- Public beta package tests: `tests.test_beta_package` — 3 tests OK.
- Public launch site tests: `tests.test_public_launch_site` — 2 tests OK.
- Full suite: `Ran 47 tests in 13.660s`, `OK`.
- Compile gate: `python3.11 -m compileall -q src examples tests` exit 0.
- Diff hygiene: `git diff --check` exit 0.
- Credential-pattern scan over changed diff: `hits= []`.
- Real smoke: `demo-local --once --agent-port 0 --ui-port 8092 --runs-dir /tmp/agentstack-offline-demo-once --run-id offline-mvp-proof` returned:
  - `mode=offline-local-demo`
  - `internetRequired=False`
  - `apiKeysRequired=False`
  - `overall=98.88`
  - `tasks=5/5`
  - `report_exists=True`
- Long-lived UI proof:
  - `demo-local --agent-port 8766 --ui-port 8092 --runs-dir /tmp/agentstack-offline-mvp-ui --run-id offline-mvp-ui`
  - Health HTTP 200.
  - Report HTTP 200.
  - Leaderboard HTTP 200.
  - Browser visual proof showed `Offline Demo Agent`, `Overall 98.88`, `5/5 tasks`, `local-public`, and readable dimensions.
