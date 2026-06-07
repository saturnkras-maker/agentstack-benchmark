# Auth and rate-limit scaffold v0.1

This slice adds a local-safe security scaffold for the free-beta preview server. It prepares the public beta package for guarded deployment later, without deploying anything and without storing or printing secrets.

## What is implemented

- Optional bearer-token auth for preview surfaces.
- Public health metadata that reports whether auth/rate limits are configured.
- In-memory per-client fixed-window rate limiting for the stdlib preview server.
- CLI plumbing that reads a token from an environment variable name, never from a command-line literal.
- JSON error responses for auth/rate-limit failures.

## Defaults

When the Python API is used directly with `make_server(...)`, security defaults to disabled for backward-compatible local tests.

When the CLI preview server is started with `serve`, rate limiting is enabled by default:

- `--rate-limit-requests 120`
- `--rate-limit-window-seconds 60`

Bearer auth is disabled unless `--api-token-env` is provided and the referenced environment variable is set.

## Start with rate limiting only

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli serve \
  --host 127.0.0.1 \
  --port 8088 \
  --runs-dir artifacts/runs
```

## Start with bearer auth

Use an environment variable name. Do not put token values in shell history, docs, commits, or artifacts.

```bash
export AGENTSTACK_BENCHMARK_API_TOKEN="<set-locally>"
PYTHONPATH=src python3 -m agentstack_benchmark.cli serve \
  --host 127.0.0.1 \
  --port 8088 \
  --runs-dir artifacts/runs \
  --api-token-env AGENTSTACK_BENCHMARK_API_TOKEN
```

Client requests then use:

```bash
curl http://127.0.0.1:8088/api/v1/tracks  # add Authorization bearer header in the client
```

## Public metadata

`GET /api/v1/healthz` stays public and includes safe metadata only:

```json
{
  "status": "ok",
  "service": "agentstack-benchmark",
  "pricingMode": "free-beta",
  "security": {
    "schemaVersion": "agentstack-benchmark.security.v0.1",
    "auth": {
      "enabled": true,
      "mode": "bearer",
      "tokenConfigured": true
    },
    "rateLimit": {
      "enabled": true,
      "requests": 120,
      "windowSeconds": 60
    }
  }
}
```

Token values are never included in the metadata.

## Error responses

Missing bearer token:

- HTTP `401`
- `WWW-Authenticate: Bearer`
- JSON error code `AUTH_REQUIRED`

Wrong bearer token:

- HTTP `403`
- JSON error code `AUTH_INVALID`

Rate limit exceeded:

- HTTP `429`
- `Retry-After: <seconds>`
- JSON error code `RATE_LIMITED`

## Not implemented here

This is not production hosting. This slice does **not** add:

- external deploy;
- public launch;
- billing/payment flows;
- production secret management;
- hosted runner or hidden task corpus;
- distributed rate limiting;
- persistent auth users/roles.

## Verification

```bash
PYTHONPATH=src python3 -m unittest tests.test_security -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src examples tests
```
