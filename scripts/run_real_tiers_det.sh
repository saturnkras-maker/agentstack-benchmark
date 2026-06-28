#!/usr/bin/env bash
# P2 validation companion: same 3 real tiers but DETERMINISTIC path only
# (no --judge), to show the default scoring is already sensible.
set -u
ROOT="/home/user/.openclaw/workspace/worktrees/agentstack-p2-honest-scoring"
CLAUDE_BIN="/home/user/.local/bin/claude"
AGENT="$ROOT/examples/agents/claude_real_http_agent.py"
OUT_BASE="$ROOT/artifacts/real-runs-v1det"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT/src"
mkdir -p "$OUT_BASE"

run_tier () {
  local name="$1" model="$2" port="$3" manifest="$4"
  local out="$OUT_BASE/$name" log="$OUT_BASE/$name.agent.log"
  echo "=== TIER $name (model=$model port=$port) [deterministic] ==="
  python3 "$AGENT" --host 127.0.0.1 --port "$port" --model "$model" \
      --claude-bin "$CLAUDE_BIN" --call-timeout 115 >"$log" 2>&1 &
  local agent_pid=$!
  for _ in $(seq 1 40); do
    grep -q '"url"' "$log" 2>/dev/null && break
    kill -0 "$agent_pid" 2>/dev/null || { echo "AGENT died:"; cat "$log"; return 1; }
    sleep 0.25
  done
  python3 -m agentstack_benchmark.cli run \
      --manifest "$manifest" \
      --task-pack "$ROOT/examples/task_packs/mvp_v0.json" \
      --out "$out" --http-timeout-seconds 120
  local rc=$?
  kill "$agent_pid" 2>/dev/null; wait "$agent_pid" 2>/dev/null
  echo "  $name done rc=$rc"
  return $rc
}

run_tier real-haiku  "claude-haiku-4-5-20251001" 8799 "$ROOT/examples/manifests/claude_real_haiku.json"  || exit 1
run_tier real-sonnet "claude-sonnet-4-6"         8800 "$ROOT/examples/manifests/claude_real_sonnet.json" || exit 1
run_tier real-opus   "claude-opus-4-8"           8801 "$ROOT/examples/manifests/claude_real_opus.json"   || exit 1
python3 -m agentstack_benchmark.cli leaderboard --runs-dir "$OUT_BASE" --out "$ROOT/artifacts/leaderboard-real-v1det.json"
echo "DET TIERS DONE"
