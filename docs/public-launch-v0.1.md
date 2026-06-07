# Public launch v0.1

This document records the first public launch surface for AgentStack Benchmark.

## Launch target

- Repository: `https://github.com/saturnkras-maker/agentstack-benchmark`
- PR gate: `https://github.com/saturnkras-maker/agentstack-benchmark/pull/1` (merged)
- Release branch: `main`
- Static launch page source: `site/`
- Deployment target: GitHub Pages via `gh-pages` branch.

## Guarantees

- No direct push to `main`.
- Public beta code reached `main` through merged PR #1.
- Launch page contains no production secrets, no private keys, and no payment credentials.
- `local-public` is the default track.
- `hosted-verified` remains reserved for a future server-side runner.

## Public beta command

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli beta-package \
  --out-dir artifacts/public-beta-package
```

## Non-goals for this launch

- No hidden task corpus.
- No hosted runner execution.
- No paid checkout until a billing provider and legal/payment workflow are configured.
