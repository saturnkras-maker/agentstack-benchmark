# Public Beta Trust & Demo Pack implementation notes

## Goal

Create a pre-manual-test trust pack for the local-public MVP:

- one-command proof loop (`make verify-local-mvp`);
- deterministic 5-pilot local leaderboard (`make demo-pilots`);
- static public demo report/leaderboard under `site/demo/`;
- GitHub Actions local MVP trust gates;
- docs/site/package updates without billing, hosted runner, API keys, or external model calls.

## Delivered surfaces

- `src/agentstack_benchmark/local_mvp_verification.py`
- `src/agentstack_benchmark/public_demo.py`
- CLI commands:
  - `verify-local-mvp`
  - `public-demo-site`
- Make targets:
  - `make verify-local-mvp`
  - `make demo-pilots`
  - `make public-demo-site`
- CI workflow:
  - `.github/workflows/ci.yml`
- Public static sample:
  - `site/demo/index.html`
  - `site/demo/report.html`
  - `site/demo/leaderboard.html`
  - `site/demo/report.json`
  - `site/demo/leaderboard.json`
  - `site/demo/public-demo.json`

## Proof before PR

- Targeted tests: 15 tests OK.
- Full unittest suite: 63 tests OK.
- Compile: `python3.11 -m compileall -q src examples tests` OK.
- Diff check: `git diff --check` OK.
- Credential pattern scan: no credential patterns found.
- `make verify-local-mvp`: status `pass`, overall `98.88`, tasks `5/5`, endpoints checked `6`.
- `make demo-pilots`: pilots `5`, leaderboard entries `5`.
- `make public-demo-site`: status `static-local-public-sample-ready`, sample overall `98.88`, leaderboard entries `5`.

## Safety boundary

No hosted runner, billing checkout, API keys, external model calls, hidden task corpus, or production credentials were added.
