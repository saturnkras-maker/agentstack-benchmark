# Local model adapter slice — implementation notes

## Goal

Add a safe local-model boundary after the offline MVP: if a user has a local Ollama/llama.cpp/OpenAI-compatible endpoint, AgentStack Benchmark can benchmark it through the same UX. If no backend is available, the product must not hang; it falls back to the deterministic offline demo.

## Discovery result on this Mac

- `llama-server`: not found.
- `llama-cli`: not found.
- `ollama`: not found.
- `.gguf` in workspace/Downloads/HF cache: not found.
- Common loopback model ports did not expose a model API.

Decision: implement adapter/autodetect boundary and prove it with a fake loopback OpenAI-compatible backend in tests; keep deterministic fallback for the live local MVP.

## Implemented

- `src/agentstack_benchmark/local_model.py`:
  - loopback-only backend discovery;
  - OpenAI-compatible `/v1/models` + `/v1/chat/completions` support;
  - Ollama `/api/tags` + `/api/chat` support;
  - local model adapter agent exposing the existing `/tasks` contract;
  - one-shot local model demo runner.
- CLI:
  - `local-model-check`;
  - `demo-local --agent-mode auto-local-model`;
  - `demo-local --agent-mode local-model`;
  - `--local-model-base-url` and `--local-model-name`.
- Docs/surfaces:
  - `docs/local-model-adapter-v0.1.md`;
  - README/offline demo/public launch/public beta package updates;
  - static launch page and `launch.json` metadata.

## Safety boundaries

- External URLs are rejected before model calls.
- Only loopback hosts are accepted.
- No model download.
- No API keys accepted or printed.
- Local results stay `track: local-public`.
- Auto mode falls back instead of hanging when no runtime is present.

## Proof before PR

Command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3.11 -m compileall -q src examples tests
PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local --agent-mode auto-local-model --once --agent-port 0 --ui-port 8098 --runs-dir /tmp/agentstack-local-model-auto-fallback --run-id auto-fallback-proof
git diff --check
```

Observed:

- `Ran 52 tests in 16.261s` / `OK`.
- Compile exit `0`.
- Actual local model check: `available=false`, `reason=no-loopback-local-model-backend-detected`, `internetRequired=false`, `apiKeysRequired=false`.
- Auto fallback smoke: `mode=offline-local-demo`, `fallbackFromLocalModel=true`, `overall=98.88`, `tasksPassed=5/5`.
- Changed diff secret scan: `[]`.
