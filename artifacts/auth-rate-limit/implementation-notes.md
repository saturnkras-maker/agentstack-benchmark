# Auth / rate-limit local scaffold slice

## Scope

Autonomous v2 mode active. This slice implements the critical-path auth/rate-limit foundation after hosted-verified boundary.

In scope:

- optional bearer-token guard for local API/web preview surfaces;
- rate-limit scaffold with deterministic in-memory counters for the stdlib preview server;
- safe public metadata that describes whether auth/rate limits are configured without exposing token values;
- CLI flags/env plumbing using variable names/placeholders only;
- docs/tests/README updates;
- one green atomic commit.

Out of scope:

- external deploy;
- public launch;
- billing/payment flows;
- private-key management;
- production secret provisioning;
- hosted runner or hidden task corpus;
- arbitrary remote run execution.

## Preflight

- Repo was clean at start: latest commit `6e24135 feat: add hosted verified track boundary`.
- Existing server is stdlib `ThreadingHTTPServer` / `BaseHTTPRequestHandler` with read-only GET surfaces.
- Existing `make_server(host, port, runs_dir)` is used by tests; auth/rate limit must be additive/backward compatible.
- Default local preview should remain usable without secrets. Auth becomes enabled only when explicitly configured with a token value, and public metadata must never include the token.

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_security.SecurityPolicyTests.test_security_metadata_never_exposes_bearer_token -v`
  - expected failure: `ModuleNotFoundError: No module named 'agentstack_benchmark.security'`.

## GREEN / verification

Implementation:

- added `src/agentstack_benchmark/security.py` with `SecurityConfig` and in-memory fixed-window rate limiter;
- wired optional bearer auth and rate-limit checks into the preview server before non-health routes;
- kept `/api/v1/healthz` public and added safe `security` metadata with no token values;
- added CLI `serve` flags: `--api-token-env`, `--rate-limit-requests`, `--rate-limit-window-seconds`;
- documented the scaffold in `docs/auth-rate-limit-v0.1.md` and README;
- added `tests/test_security.py` for metadata redaction, bearer auth, and `429` rate-limit behavior.

Verification:

- `PYTHONPATH=src python3 -m unittest tests.test_security -v`
  - result: `Ran 3 tests in 1.022s` / `OK`.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 35 tests in 10.695s` / `OK`; compile gate exit `0`.
- manual API smoke with configured bearer auth and `1` request/window rate limit:
  - `health_status 200`;
  - `auth_enabled True`;
  - `token_leaked False`;
  - missing auth returns `401` / `AUTH_REQUIRED`;
  - authorized `/api/v1/tracks` returns `200` and `defaultTrack local-public`;
  - second authorized request returns `429` with `Retry-After 60`.
- `git diff --check`
  - result: exit `0`.
- touched-file line-length check for new security files:
  - `security.py`, `cli.py`, `tests/test_security.py`: no lines over 100 chars.
