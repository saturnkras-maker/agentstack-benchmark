#!/usr/bin/env bash
# P2 validation: re-run the 3 real Claude tiers under improved scoring (with
# --judge). Subscription only (ANTHROPIC_* stripped by the agent harness),
# loopback only, --http-timeout-seconds 120. Sequential to avoid rate spikes.
set -u
ROOT="/home/user/.openclaw/workspace/worktrees/agentstack-p2-honest-scoring"
CLAUDE_BIN="/home/user/.local/bin/claude"
AGENT="$ROOT/examples/agents/claude_real_http_agent.py"
OUT_BASE="$ROOT/artifacts/real-runs-v2"
JUDGE_MODEL="claude-haiku-4-5-20251001"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT/src"
mkdir -p "$OUT_BASE"

run_tier () {
  local name="$1" model="$2" port="$3" manifest="$4"
  local out="$OUT_BASE/$name"
  local log="$OUT_BASE/$name.agent.log"
  echo "=== TIER $name (model=$model port=$port) ==="
  # Launch the real claude HTTP agent (its own --call-timeout generous for slow tiers).
  python3 "$AGENT" --host 127.0.0.1 --port "$port" --model "$model" \
      --claude-bin "$CLAUDE_BIN" --call-timeout 115 >"$log" 2>&1 &
  local agent_pid=$!
  # Wait for readiness (the agent prints a JSON line with its url on stdout).
  for _ in $(seq 1 40); do
    if grep -q '"url"' "$log" 2>/dev/null; then break; fi
    if ! kill -0 "$agent_pid" 2>/dev/null; then echo "AGENT $name died early:"; cat "$log"; return 1; fi
    sleep 0.25
  done
  echo "  agent ready (pid=$agent_pid); running benchmark with --judge ..."
  python3 -m agentstack_benchmark.cli run \
      --manifest "$manifest" \
      --task-pack "$ROOT/examples/task_packs/mvp_v0.json" \
      --out "$out" \
      --http-timeout-seconds 120 \
      --judge --judge-model "$JUDGE_MODEL" \
      --judge-cache "$out/judge-cache.json"
  local rc=$?
  kill "$agent_pid" 2>/dev/null; wait "$agent_pid" 2>/dev/null
  echo "  tier $name done (rc=$rc), report: $out/report.json"
  return $rc
}

run_tier real-haiku  "claude-haiku-4-5-20251001" 8799 "$ROOT/examples/manifests/claude_real_haiku.json"  || exit 1
run_tier real-sonnet "claude-sonnet-4-6"         8800 "$ROOT/examples/manifests/claude_real_sonnet.json" || exit 1
run_tier real-opus   "claude-opus-4-8"           8801 "$ROOT/examples/manifests/claude_real_opus.json"   || exit 1

echo "=== building v2 leaderboard ==="
python3 -m agentstack_benchmark.cli leaderboard \
    --runs-dir "$OUT_BASE" \
    --out "$ROOT/artifacts/leaderboard-real-v2.json"
echo "ALL TIERS DONE"
