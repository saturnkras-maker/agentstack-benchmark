# Makefile local MVP aliases — implementation notes

## Goal

Reduce first-run friction by adding short root-level commands for the local/offline MVP. Users should not need to memorize the long `PYTHONPATH=src python3 -m agentstack_benchmark.cli ...` incantation.

## Implemented

- Root `Makefile` with aliases:
  - `make doctor`
  - `make demo-local`
  - `make demo-local-once`
  - `make local-model-check`
  - `make demo-local-auto`
  - `make demo-local-auto-once`
  - `make serve`
  - `make test`
  - `make compile`
- README/docs/site/public beta package updated to prefer `make` commands while preserving explicit Python equivalents.
- Public beta package manifest now includes `Makefile`.

## Proof before PR

- RED: `tests.test_makefile_aliases` failed before `Makefile` existed.
- Targeted GREEN: `tests.test_makefile_aliases tests.test_beta_package tests.test_public_launch_site` → OK.
- Actual command proof:
  - `make help` printed local MVP aliases.
  - `make doctor ... DOCTOR_ARGS=--skip-local-model-probe` printed `status=ready` and `doesNotStartServers=true`.
  - `make local-model-check` printed no loopback model backend detected, no internet/API keys required.
  - `make demo-local-once ...` produced `overall=98.88`, `tasks=5/5`, report/leaderboard URLs.
- Full suite: `Ran 56 tests in 15.568s` / `OK`.
- Compile: `python3.11 -m compileall -q src examples tests` and `make compile` exit `0`.
- `git diff --check`: exit `0`.
- Changed diff secret scan: `[]`.
