# Beta task pack implementation notes

## Scope

- Start Phase 4 by expanding beyond the 5-task MVP pack toward a launch-ready deterministic beta pack.
- Keep the pack synthetic and deterministic so the benchmark remains cheap and reproducible before hidden/private tasks exist.
- Preserve existing `mvp_v0.json` and add a separate `beta_v0_1.json`.

## Decisions / assumptions

- Use 20 tasks in this slice, covering core, tool-use, safety, memory/skills, and speed/cost categories.
- Extend the mock good agent to pass the beta pack; keep the bad agent intentionally shallow/leaky.

## Verification log

- RED: `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_beta_task_pack_has_launch_ready_category_coverage -v` failed as expected with `FileNotFoundError` for `examples/task_packs/beta_v0_1.json`.
- GREEN specific: `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_beta_task_pack_has_launch_ready_category_coverage tests.test_runner.RunnerTests.test_good_agent_scores_higher_on_beta_task_pack -v` passed: 2 tests in 0.764s.
- GREEN suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` passed: 8 tests in 2.951s.
- Compile gate: `python3 -m compileall -q src examples tests` exited 0 with no stdout.
- Manual beta smoke: good mock on `examples/task_packs/beta_v0_1.json` returned overall `98.84`; bad mock returned overall `24.97`. Temporary smoke run dirs were removed after proof.
