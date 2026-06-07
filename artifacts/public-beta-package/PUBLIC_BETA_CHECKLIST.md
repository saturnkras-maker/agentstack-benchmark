# AgentStack Benchmark public beta package

Package status: **local-ready**.

## Included trust foundation

- Local-public run track with closed enum semantics.
- HTTP adapter contract for local-only preview integrations.
- Frozen deterministic scoring schema v1.
- Reproducibility hash, variance/confidence metadata, and output redaction.
- Five local-public pilot fixtures and a track-aware leaderboard path.
- Hosted-verified boundary scaffold with hidden-task rejection in local runs.
- Optional bearer-auth and rate-limit scaffold for guarded preview serving.

## Launch boundary

- No external deploy has been performed.
- No public launch or announcement has been performed.
- No billing/payment flow is included.
- No production credential material is included.
- No hosted runner or hidden task corpus is included.

## Local verification commands

- `PYTHONPATH=src python3 -m unittest tests.test_beta_package -v`
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- `python3 -m compileall -q src examples tests`
- `PYTHONPATH=src python3 -m agentstack_benchmark.cli pilot-run --out-dir artifacts/runs/pilots-local-public-v0-1`
- `PYTHONPATH=src python3 -m agentstack_benchmark.cli serve --host 127.0.0.1 --port 8088 --runs-dir artifacts/runs`

## Required release assets

- `README.md` — sha256 `edfd3e4009fc2689b86832a022ab511de0e4a961c500923cbfca9d7aa73d7877`
- `pyproject.toml` — sha256 `e337bb8cc7b90d0efcc3b6a81e52a7a1e998b7be866dc4b53d7fff5e5e7070ae`
- `docs/product-technical-spec-v0.1.md` — sha256 `51d37884f55ace62c138966dc349349f7613f2c1374c9adc46e37d59873c2150`
- `docs/monetization-v0.md` — sha256 `86890a9cf327ec220fabaa226eeb382edfd5066345c06ea5f0848fd6ad6c4168`
- `docs/adapter-contract-v0.1.md` — sha256 `e4a7573cb3510e0c6664bfb1ef7e22bf875d7016993658abd644259c593641d9`
- `docs/scoring-schema-v1.md` — sha256 `108816d76841b93e6a0f0f136509740fc16a4caeadce0ba6ff4076e03ded8370`
- `docs/reproducibility-redaction.md` — sha256 `f66c655b67c942624c98f63ada1d63e74568871a997960ab21582c4641f249bc`
- `docs/local-public-pilots-v0.1.md` — sha256 `e0ea14dbbd4c95a11d283e4cf4daaeac012f7e47c9c5f249a5da1abce334380b`
- `docs/hosted-verified-track-v0.1.md` — sha256 `3bf988659da32031177b37fac8f1ee777bb7db1106a53fd5f3db48220a5922ef`
- `docs/auth-rate-limit-v0.1.md` — sha256 `37ca5133c9188341993c3c3681665bd9021ad0debfc06db59c24f9eab2604dd7`
- `docs/public-beta-package-v0.1.md` — sha256 `cf64901d03c0e9d6b8252dd6845bf7f53a8cc77414899700e99707a5b424c2e0`
- `examples/task_packs/beta_v0_1.json` — sha256 `ec0b783e56e51ded15ee2f8111db5bf42e64615ec4bdfc7fc497b79b8df9546d`
- `examples/pilots/local_public_v0_1.json` — sha256 `03d44516e4af70ade9a3c5ddf1a1c2367a74e91e592d009ed3162dd26d163c6b`
