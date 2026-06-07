# Hosted-verified track boundary v0.1

This document freezes the **local-safe boundary** for the future `hosted-verified` track. It is intentionally a scaffold, not a hosted runner implementation.

## Track capabilities

Machine-readable capabilities are exposed by:

```bash
GET /api/v1/tracks
```

The response wrapper uses the existing beta API shape:

```json
{
  "service": "agentstack-benchmark",
  "pricingMode": "free-beta",
  "trackCapabilities": {
    "schemaVersion": "agentstack-benchmark.track-capabilities.v0.1",
    "defaultTrack": "local-public",
    "tracks": []
  }
}
```

## Track meanings

- `local-public`
  - status: `active`;
  - assignment authority: local runner;
  - local runner may assign this track;
  - task visibility: public tasks only;
  - hidden tasks are rejected before report persistence.

- `hosted-verified`
  - status: `reserved`;
  - assignment authority: future server-side hosted runner;
  - local runner must not assign this track;
  - task visibility: public + hidden tasks;
  - requires hosted infrastructure that is not implemented in this slice.

## Anti-cheat boundary

The local/open-source runner is intentionally not allowed to create `hosted-verified` reports. `hosted-verified` credibility depends on server-side task custody and controlled execution. If a local task pack includes a hidden task marker, the local runner raises a validation error instead of running it or writing a report artifact.

Hidden-task markers currently recognized by the local guard:

- `"visibility": "hidden"`;
- `"hidden": true`;
- `"requiresTrack": "hosted-verified"`.

Unknown visibility values are rejected. Missing visibility defaults to public.

## Not implemented here

This slice deliberately does **not** add:

- hidden task corpus;
- hosted execution service;
- remote verification signing;
- auth or rate limits;
- public launch/deploy;
- billing;
- private key or credential flows.

## Local verification

Run the boundary tests:

```bash
PYTHONPATH=src python3 -m unittest tests.test_tracks -v
```

Run the full local suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src examples tests
```
