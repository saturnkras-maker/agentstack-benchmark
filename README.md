# AgentStack Benchmark

Prototype “3DMark for AI agents”: a benchmark kernel for evaluating complete agent stacks, not only base models.

Current slice:

- local CLI runner;
- JSON agent manifest;
- JSON task pack;
- CLI adapter;
- deterministic evaluator;
- JSON + Markdown reports;
- mock good/bad agents;
- unit tests proving score separation.

Run demo:

```bash
PYTHONPATH=src python3 -m agentstack_benchmark.cli run \
  --manifest examples/manifests/mock_good.json \
  --task-pack examples/task_packs/mvp_v0.json \
  --out artifacts/runs/demo-good
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Product/technical spec: `docs/product-technical-spec-v0.1.md`.
