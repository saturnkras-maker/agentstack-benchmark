# Local model adapter v0.1

This slice adds a safe boundary for testing a real local model backend through the same AgentStack Benchmark UX.

It does **not** download models, require internet, accept API keys, or expose external endpoints. Everything is loopback-only by default.

## What is supported

- OpenAI-compatible local endpoints, for example `llama-server` with `/v1/models` and `/v1/chat/completions`.
- Ollama loopback endpoints with `/api/tags` and `/api/chat`.
- Automatic fallback to the deterministic offline demo when `auto-local-model` is selected and no local model backend is reachable.

## Check local model availability

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check
```

Probe a specific OpenAI-compatible local endpoint:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check \
  --base-url http://127.0.0.1:8080/v1
```

Expected no-model result is explicit and non-blocking, for example:

```json
{"available": false, "provider": "none", "reason": "no-loopback-local-model-backend-detected"}
```

## Run the demo with local-model autodetect

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local \
  --agent-mode auto-local-model
```

Behavior:

- If a loopback local model backend is available, AgentStack starts a local model adapter agent and benchmarks it.
- If no backend is available, AgentStack falls back to the deterministic offline demo and includes `fallbackFromLocalModel: true` in CLI JSON.

Use strict local-model mode when fallback should be disabled:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local \
  --agent-mode local-model \
  --local-model-base-url http://127.0.0.1:8080/v1
```

If the backend is unavailable, strict mode exits non-zero and prints the local model status.

## Example with llama.cpp

If `llama-server` is installed and a GGUF is already local, start it separately. Example shape:

```bash
llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
```

Then run:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local \
  --agent-mode local-model \
  --local-model-base-url http://127.0.0.1:8080/v1
```

## Example with Ollama

If Ollama and a model are already installed locally:

```bash
ollama serve
ollama run <local-model-name>
```

Then run:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local \
  --agent-mode local-model \
  --local-model-base-url http://127.0.0.1:11434 \
  --local-model-name <local-model-name>
```

## Safety boundaries

- External URLs are rejected before any model call.
- Only loopback hosts are allowed: `127.0.0.1`, `localhost`, and `::1`.
- No API keys are accepted or printed by this slice.
- No model download is attempted.
- Results stay `local-public`; this does not create `hosted-verified` evidence.
