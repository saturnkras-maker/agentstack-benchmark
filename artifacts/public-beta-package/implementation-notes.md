# Public beta package slice

## Scope

Autonomous v2 mode active. This slice turns the completed local-public beta foundation into a local release package artifact.

In scope:

- machine-readable public beta package manifest;
- human-readable readiness checklist;
- CLI generator for a local package directory;
- tests proving the package references current docs/examples and preserves the no-deploy/no-billing/no-secret boundary.

Out of scope:

- external deploy;
- public launch or announcements;
- billing/payment flows;
- production secrets;
- hosted runner execution;
- hidden task corpus.

## Preflight sources inspected

- `README.md`
- `pyproject.toml`
- `docs/product-technical-spec-v0.1.md`
- `docs/monetization-v0.md`
- existing slice docs under `docs/`
- current CLI surfaces in `src/agentstack_benchmark/cli.py`

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_beta_package.PublicBetaPackageTests.test_public_beta_package_manifest_covers_release_critical_assets -v`
  - expected failure: `ModuleNotFoundError: No module named 'agentstack_benchmark.beta_package'`.

## GREEN / verification

Implementation:

- added `src/agentstack_benchmark/beta_package.py` with manifest/checklist/summary generation;
- added `agentstack-benchmark beta-package` CLI command;
- added `docs/public-beta-package-v0.1.md`;
- updated README with the local package generation command;
- added `tests/test_beta_package.py` for manifest assets, no-deploy/no-billing boundary, and CLI output.

Verification:

- `PYTHONPATH=src python3 -m unittest tests.test_beta_package -v`
  - result: `Ran 3 tests in 0.003s` / `OK`.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 38 tests in 10.583s` / `OK`; compile gate exit `0`.
- manual package smoke:
  - command: `PYTHONPATH=src python3 -m agentstack_benchmark.cli beta-package --out-dir /tmp/agentstack-public-beta-package`;
  - `manifest_schema agentstack-benchmark.public-beta-package.v0.1`;
  - `packageStatus local-ready`;
  - `assetCount 13`;
  - `pricingMode free-beta`;
  - `defaultTrack local-public`;
  - `launchActionsPerformed False`;
  - `checklistHasNoDeploy True`;
  - `checklistHasNoBilling True`;
  - `hasAbsoluteAssetPath False`;
  - `sensitiveWordsInManifest False`.
- `git diff --check`
  - result: exit `0`.
- touched-file line-length check for new package files:
  - `beta_package.py`, `cli.py`, `tests/test_beta_package.py`: no lines over 100 chars.
