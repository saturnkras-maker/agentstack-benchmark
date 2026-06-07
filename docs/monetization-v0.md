# Monetization v0 — Free Beta First

## Current decision

AgentStack Benchmark launches first as a **free beta service**.

Free beta includes:

- public basic benchmark run;
- public leaderboard entry;
- short public report;
- adapter/manifest documentation;
- reproducibility and trace metadata where safe to publish.

## Why free first

- The immediate product risk is trust and benchmark usefulness, not revenue capture.
- We need real submitted agent stacks to tune task packs, scoring, reports, and anti-cheat.
- A free public leaderboard creates distribution and social proof faster than a paywall.

## Deferred paid surfaces

Paid features should wait until free beta proves repeat usage:

- private benchmark runs;
- private/deep trace breakdown;
- improvement recommendations;
- compare-with-competitors report;
- historical tracking;
- team dashboard;
- API access;
- verified/reproducible badge;
- custom task packs.

## Boundary for implementation

- Do not add payments, wallets, private keys, or billing flows in MVP v0.1.
- Keep pricing state explicit as `free-beta` in API/docs so it can evolve later.
