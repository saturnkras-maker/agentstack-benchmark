# Adapter contract slice

## Scope

Autonomous v2 mode active. This slice implements the next critical-path item: adapter contract.

In scope:

- versioned HTTP adapter request contract;
- machine-readable contract output for self-serve implementers;
- response validation/normalization for untrusted adapter responses;
- docs/README update for a minimal local HTTP handler path;
- tests proving request/response fields and no answer leakage.

Out of scope:

- hidden tasks;
- hosted/verified track execution;
- auth/rate limits;
- scoring_schema_v1 freeze;
- reproducibility/redaction;
- external deploy/public launch/billing/live external actions/private-key flows.

## Preflight

- `git status --short --branch` → `## main`
- latest commit: `b50f401 feat: add run track field`
- repo clean before edits.
- inspected: README, runner, CLI, product technical spec, mock HTTP manifest, current tests.

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_adapter_contract.AdapterContractTests.test_task_request_is_versioned_and_does_not_leak_expected_answer -v`
  - expected failure: `ModuleNotFoundError: No module named 'agentstack_benchmark.adapter_contract'`.

## Implementation decisions

- Added versioned contract constants:
  - `agentstack-benchmark.adapter.contract.v0.1`
  - `agentstack-benchmark.adapter.request.v0.1`
  - `agentstack-benchmark.adapter.response.v0.1`
- HTTP/CLI task payloads now use canonical request order: `schemaVersion`, `taskId`, `category`, `prompt`, `context`, `timeoutSeconds`.
- Runner does not send `expected`, `budgetUsd`, or `depthKeywords` to adapters.
- HTTP response body is treated as untrusted and must be a JSON object with string `answer` and string-array `toolTrace`; invalid shapes produce `invalid_adapter_response` output for the attempt.
- Added `adapter-contract` CLI for machine-readable contract JSON.
- Added `docs/adapter-contract-v0.1.md` and `examples/agents/http_contract_agent.py` for a local handler onboarding path.
- Kept local-only HTTP endpoint guard unchanged: loopback HTTP only.

## GREEN / verification

- Targeted adapter-contract tests:
  - `PYTHONPATH=src python3 -m unittest tests.test_adapter_contract -v`
  - result: `Ran 4 tests in 0.512s` / `OK`.
- Full suite + compile gate:
  - `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 21 tests in 8.527s` / `OK`; compile gate exit `0`.
- Manual local smoke:
  - started `examples/agents/http_contract_agent.py` on `127.0.0.1:18765`;
  - generated machine-readable contract via `adapter-contract`;
  - ran benchmark against temp HTTP manifest and MVP pack;
  - observed:
    - `contract_schema=agentstack-benchmark.adapter.contract.v0.1`
    - `request_schema=agentstack-benchmark.adapter.request.v0.1`
    - `response_schema=agentstack-benchmark.adapter.response.v0.1`
    - `track=local-public`
    - `overall=98.88`
    - `tasks=5/5`
  - HTTP example server process was killed after smoke.
