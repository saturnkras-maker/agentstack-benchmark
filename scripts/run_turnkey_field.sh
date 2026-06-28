#!/usr/bin/env bash
# TURNKEY validation: run a DIVERSE real field on the richer_v1 pack with --judge
# to prove the benchmark SEPARATES weak->strong:
#   - 3 competent real Claude tiers (Haiku / Sonnet / Opus) on subscription, AND
#   - 1 DELIBERATELY-WEAK real agent: the same Haiku model + real inference, but
#     handicapped via an appended system prompt ("answer in <=5 words, no
#     reasoning"). Real inference, intentionally shallow -> must land clearly
#     BELOW the competent tiers.
# Subscription only (ANTHROPIC_* stripped by the agent harness + the judge),
# loopback only, --http-timeout-seconds 120. Sequential to avoid rate spikes.
set -u
ROOT="/home/user/.openclaw/workspace/worktrees/agentstack-integration"
CLAUDE_BIN="/home/user/.local/bin/claude"
AGENT="$ROOT/examples/agents/claude_real_http_agent.py"
PACK="$ROOT/examples/task_packs/richer_v1.json"
OUT_BASE="$ROOT/artifacts/turnkey-real-v1"
JUDGE_MODEL="claude-haiku-4-5-20251001"
WEAK_SYSTEM_PROMPT="STRICT OUTPUT RULE — you MUST obey: reply with at most 5 words total. Do NOT show any reasoning, steps, calculations, working, or explanation. Output ONLY a single short final answer of 5 words or fewer. Any extra words is a failure."
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT/src"
mkdir -p "$OUT_BASE"

free_port () {
  local port="$1" pid
  pid="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$pid" ]; then
    echo "  freeing port $port (stale listener pid=$pid)"
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
}

run_tier () {
  local name="$1" model="$2" port="$3" manifest="$4" sysprompt="${5:-}"
  local out="$OUT_BASE/$name"
  local log="$OUT_BASE/$name.agent.log"
  echo "=== TIER $name (model=$model port=$port handicap=$([ -n "$sysprompt" ] && echo yes || echo no)) ==="
  free_port "$port"
  if [ -n "$sysprompt" ]; then
    python3 "$AGENT" --host 127.0.0.1 --port "$port" --model "$model" \
        --claude-bin "$CLAUDE_BIN" --call-timeout 115 \
        --max-attempts 5 --retry-backoff 5 --system-prompt "$sysprompt" >"$log" 2>&1 &
  else
    python3 "$AGENT" --host 127.0.0.1 --port "$port" --model "$model" \
        --claude-bin "$CLAUDE_BIN" --call-timeout 115 \
        --max-attempts 5 --retry-backoff 5 >"$log" 2>&1 &
  fi
  local agent_pid=$!
  for _ in $(seq 1 40); do
    if grep -q '"url"' "$log" 2>/dev/null; then break; fi
    if ! kill -0 "$agent_pid" 2>/dev/null; then echo "AGENT $name died early:"; cat "$log"; return 1; fi
    sleep 0.25
  done
  echo "  agent ready (pid=$agent_pid); running RICHER benchmark with --judge ..."
  mkdir -p "$out"
  python3 -m agentstack_benchmark.cli run \
      --manifest "$manifest" \
      --task-pack "$PACK" \
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
run_tier weak-haiku  "claude-haiku-4-5-20251001" 8802 "$ROOT/examples/manifests/claude_real_weak.json"   "$WEAK_SYSTEM_PROMPT" || exit 1

echo "=== building turnkey diverse-field leaderboard ==="
python3 -m agentstack_benchmark.cli leaderboard \
    --runs-dir "$OUT_BASE" \
    --out "$ROOT/artifacts/leaderboard-turnkey-v1.json"
echo "ALL TURNKEY TIERS DONE"
