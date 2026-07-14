#!/usr/bin/env bash
# agy_arm.sh — run the "Google Antigravity harness" comparison arm end-to-end for one pair+variant.
#
#   export prompt (byte-identical to the pipeline's own translation stage)
#     → run the Antigravity CLI (`agy`) headless on it (chat mode: no tools expected — the
#       adaptation prompt demands a pure fenced-block answer, and CWD is an isolated export dir)
#     → save the answer as capture.md
#     → score it with the pipeline's own gauntlet (score_external.py: same assembler, same
#       sandboxes, same execution-equivalence)
#
# COSTS ANTIGRAVITY QUOTA (your Google account). Run deliberately, one pair at a time.
# Needs the LIVE stack (e-INFRA for extract/schema-inspection during export, Daytona + WWI DBs for
# scoring) and the orchestrator venv.
#
# Usage (from services/orchestrator):
#   evaluation/scripts/agy_arm.sh <pair> [variant] [model]
#   evaluation/scripts/agy_arm.sh dapper-mongodb full "Gemini 3.1 Pro (High)"
#
#   pair    : dapper-mongodb | dapper-neo4j | efcore-mongodb | efcore-neo4j |
#             nhibernate-mongodb | nhibernate-neo4j
#   variant : full (default) | batch1 | batch2 | batch3 | small
#   model   : an `agy models` display name, QUOTED (default: "Gemini 3.1 Pro (High)").
#             The comparison matrix runs "Gemini 3.5 Flash (High)" and "Gemini 3.1 Pro (High)".
#
# FAIRNESS NOTE vs claude_arm.sh: agy has no --append-system-prompt flag, so the exported
# system.txt is PREPENDED to the user prompt under an explicit "SYSTEM PROMPT" header — byte-equal
# knowledge, slightly different framing (state this in the thesis). Everything else is identical:
# same export, same no-tools contract, same isolated CWD, same scorer.
set -euo pipefail

PAIR="${1:?pair required (e.g. dapper-mongodb)}"
VARIANT="${2:-full}"
MODEL="${3:-Gemini 3.1 Pro (High)}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"   # services/orchestrator
OUT_ROOT="$ROOT/evaluation/manual-eval/wwi"

cd "$ROOT"

# ---- 1. export (reuse newest existing export unless FRESH=1) — shared with claude_arm.sh
EXPORT_DIR="$(ls -dt "$OUT_ROOT/${PAIR}__${VARIANT}__"*/ 2>/dev/null | head -1 || true)"
if [[ -z "$EXPORT_DIR" || "${FRESH:-0}" == "1" ]]; then
  echo "== exporting prompt for $PAIR [$VARIANT] (drives the live graph up to the model call)"
  uv run python evaluation/scripts/export_manual_prompts.py --pair "$PAIR" --variant "$VARIANT" \
    --out evaluation/manual-eval --env .env.dev
  EXPORT_DIR="$(ls -dt "$OUT_ROOT/${PAIR}__${VARIANT}__"*/ | head -1)"
fi
EXPORT_DIR="${EXPORT_DIR%/}"
echo "== export: $EXPORT_DIR"

# ---- 2. run agy headless, isolated CWD; system prompt prepended (agy has no system-prompt flag)
PROMPT_FILE="$EXPORT_DIR/.combined-agy-prompt.txt"
{
  echo "SYSTEM PROMPT (follow it for the whole task):"
  echo
  cat "$EXPORT_DIR/system.txt"
  printf '\n\n---\n\nUSER REQUEST:\n\n'
  cat "$EXPORT_DIR/user.txt"
  printf '\n\n'
  cat "$EXPORT_DIR/adaptation.txt"
} > "$PROMPT_FILE"

# slugify the display name for the results label: "Gemini 3.1 Pro (High)" -> gemini-3.1-pro-high
MODEL_LABEL="$(echo "$MODEL" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9.]+/-/g; s/^-+|-+$//g')"
# Per-model capture name: several models run against ONE shared export — no overwrites.
CAPTURE="$EXPORT_DIR/capture-antigravity-${MODEL_LABEL}.md"

echo "== running: agy --print --model \"$MODEL\" (prompt: $(wc -c < "$PROMPT_FILE") bytes) — this spends Antigravity quota"
START=$(date +%s)
# echo "agy --model $MODEL --print-timeout 30m --print '$(cat "$PROMPT_FILE")'" > "$EXPORT_DIR/command.md"

AGY_PROMPT="$(cat "$PROMPT_FILE")"
(cd "$EXPORT_DIR" && agy --model "$MODEL" --print-timeout 30m --print "$AGY_PROMPT" > "$CAPTURE")
WALL=$(( $(date +%s) - START ))
echo "== captured $(wc -c < "$CAPTURE") bytes in ${WALL}s -> $CAPTURE"

# ---- 3. score with the pipeline's own gauntlet
uv run python evaluation/scripts/score_external.py \
  --capture "$CAPTURE" \
  --pair "$PAIR" --variant "$VARIANT" \
  --approach antigravity --model-label "$MODEL_LABEL" \
  --out evaluation/out/external --pred-root evaluation/predictions --env .env.dev

echo "== done. generation wall clock (agy side): ${WALL}s"
