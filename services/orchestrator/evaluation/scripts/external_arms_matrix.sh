#!/usr/bin/env bash
# external_arms_matrix.sh — run the FULL external-harness comparison matrix (user-triggered; spends
# Claude tokens + Antigravity quota):
#
#   claude_code arm : claude-opus-4-8, claude-sonnet-5      (all --effort high)
#   antigravity arm : "Gemini 3.5 Flash (High)", "Gemini 3.1 Pro (High)"   (via agy CLI)
#   × pairs         : all 6 (or pass a subset)
#
# Each cell = export (reused per pair) → headless generation → score_external (same gauntlet as the
# pipeline). Results accumulate in evaluation/out/external/<approach>/results.csv; compare with
# compare_arms.py.
#
# Usage (from services/orchestrator):
#   evaluation/scripts/external_arms_matrix.sh                 # everything
#   evaluation/scripts/external_arms_matrix.sh claude          # claude arm only
#   evaluation/scripts/external_arms_matrix.sh agy             # antigravity arm only
#   PAIRS="dapper-neo4j efcore-neo4j" evaluation/scripts/external_arms_matrix.sh claude
#
# Cells run SEQUENTIALLY on purpose: score_external compiles+runs both sandboxes, and concurrent
# scoring runs would contend for the Daytona stack (and skew each other's wall-clock).
set -euo pipefail

ARM="${1:-all}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PAIRS="${PAIRS:-dapper-mongodb dapper-neo4j efcore-mongodb efcore-neo4j nhibernate-mongodb nhibernate-neo4j}"
VARIANT="${VARIANT:-full}"

CLAUDE_MODELS=(claude-sonnet-5)
AGY_MODELS=("Gemini 3.5 Flash (High)" "Gemini 3.1 Pro (High)")

FAILED=()
for pair in $PAIRS; do
  if [[ "$ARM" == "all" || "$ARM" == "claude" ]]; then
    for model in "${CLAUDE_MODELS[@]}"; do
      echo; echo "######## claude_code | $pair | $model (high) ########"
      "$HERE/claude_arm.sh" "$pair" "$VARIANT" "$model" high \
        || { echo "!! FAILED: claude_code $pair $model"; FAILED+=("claude_code/$pair/$model"); }
    done
  fi
  if [[ "$ARM" == "all" || "$ARM" == "agy" ]]; then
    for model in "${AGY_MODELS[@]}"; do
      echo; echo "######## antigravity | $pair | $model ########"
      "$HERE/agy_arm.sh" "$pair" "$VARIANT" "$model" \
        || { echo "!! FAILED: antigravity $pair $model"; FAILED+=("antigravity/$pair/$model"); }
    done
  fi
done

echo
if ((${#FAILED[@]})); then
  echo "== matrix done with ${#FAILED[@]} failure(s):"; printf '   %s\n' "${FAILED[@]}"
  exit 1
fi
echo "== matrix done. Head-to-head table:"
echo "   uv run python evaluation/scripts/compare_arms.py \\"
echo "     --pipeline our_approach=evaluation/out/agg-9-7/summary_by_pair.csv \\"
echo "     --external claude_code=evaluation/out/external/claude_code/results.csv \\"
echo "     --external antigravity=evaluation/out/external/antigravity/results.csv"
