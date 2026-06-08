# Public demo sample v0.1

The public launch page includes a static sample demo under `site/demo/`.

Generate it with:

```bash
make public-demo-site
```

Equivalent explicit command:

```bash
PYTHONPATH=src python3.11 -m agentstack_benchmark.cli public-demo-site --out-dir site/demo
```

## Files

- `site/demo/index.html` — static demo landing page.
- `site/demo/report.html` — visual sample report for the deterministic Offline Demo Agent.
- `site/demo/leaderboard.html` — static 5-pilot local-public leaderboard.
- `site/demo/report.json` — public JSON sample report.
- `site/demo/leaderboard.json` — public JSON sample leaderboard.
- `site/demo/public-demo.json` — metadata and safety boundary.

## What it represents

The sample is a static local-public artifact. It lets visitors inspect the report and leaderboard shape before cloning the repository.

It does **not** represent hosted execution:

- no hosted runner;
- no billing checkout;
- no API keys;
- no external model call;
- no hidden tasks;
- no verified badge.

For real local testing, use:

```bash
make verify-local-mvp
make demo-local
make cockpit
make demo-pilots
```
