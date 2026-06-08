# Public beta package v0.1

The public beta package is a **local release artifact** for AgentStack Benchmark. It collects the files, commands, and trust-boundary notes needed to review or hand off the free beta without performing an external launch.

## Generate the package

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli beta-package \
  --out-dir artifacts/public-beta-package
```

Generated files:

- `public_beta_manifest.json` — machine-readable package manifest;
- `PUBLIC_BETA_CHECKLIST.md` — human-readable readiness checklist;
- `summary.json` — compact generator output for automation.

## Manifest guarantees

The manifest declares:

- `schemaVersion: agentstack-benchmark.public-beta-package.v0.1`;
- `packageStatus: local-ready`;
- `pricingMode: free-beta`;
- `defaultTrack: local-public`;
- `hostedVerifiedStatus: reserved-server-side-only`;
- `deploymentStatus: local-artifact-not-deployed`;
- `billingStatus: deferred-no-payment-flow`;
- `launchActionsPerformed: false`.

Every listed release asset uses a repository-relative path and a SHA-256 file hash. This makes the package reviewable without embedding absolute local paths or sensitive runtime values.

## Included release-critical assets

The generator currently requires these source assets:

- `README.md`;
- `pyproject.toml`;
- product/monetization docs;
- adapter contract docs;
- frozen scoring schema docs;
- reproducibility/redaction docs;
- local-public pilot docs and registry;
- hosted-verified boundary docs;
- auth/rate-limit docs;
- offline local MVP demo docs;
- local model adapter docs;
- first-run doctor docs;
- Local MVP Cockpit docs;
- offline demo manifest;
- deterministic beta task pack.

## Explicit non-actions

The package does not perform or imply:

- external deploy;
- public launch/announcement;
- billing/payment setup;
- production credential provisioning;
- hosted runner execution;
- hidden task publication.

Those remain separate decisions even when the local package is green.

## Verification

```bash
PYTHONPATH=src python3 -m unittest tests.test_beta_package -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src examples tests
make doctor
make demo-local-once
make cockpit
make local-model-check
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local --once
PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check
PYTHONPATH=src python3 -m agentstack_benchmark.cli doctor
PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local --agent-mode auto-local-model --once
```
