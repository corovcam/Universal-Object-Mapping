#!/usr/bin/env bash
# claude_arm.sh — run the "Anthropic harness" comparison arm end-to-end for one pair+variant.
#
#   export prompt (byte-identical to the pipeline's own translation stage)
#     → run Claude Code headless on it (chat mode: NO tools — same constraint as the exported
#       prompt states; the model answers from its own knowledge, like the manual chat arms)
#     → save the answer as capture.md
#     → score it with the pipeline's own gauntlet (score_external.py: same assembler, same
#       sandboxes, same execution-equivalence)
#
# COSTS CLAUDE TOKENS (your Claude Code subscription/API). Run deliberately, one pair at a time.
# Needs the LIVE stack (e-INFRA for extract/schema-inspection during export, Daytona + WWI DBs for
# scoring) and the orchestrator venv.
#
# Usage (from services/orchestrator):
#   evaluation/scripts/claude_arm.sh <pair> [variant] [model] [effort]
#   evaluation/scripts/claude_arm.sh dapper-mongodb full claude-opus-4-8 high
#
#   pair    : dapper-mongodb | dapper-neo4j | efcore-mongodb | efcore-neo4j |
#             nhibernate-mongodb | nhibernate-neo4j
#   variant : full (default) | batch1 | batch2 | batch3 | small
#   model   : Claude Code --model value (default: the CLI's default model)
#   effort  : Claude Code --effort value: low|medium|high|xhigh|max (default: high —
#             the comparison matrix runs opus-4.8/fable-5/sonnet-5 all at high)
#
# The Claude call runs with CWD = the export folder so the repo's CLAUDE.md / code / predictions
# are NOT in its context — the arm sees exactly what a chat UI would see. Re-running reuses the
# newest existing export for the pair+variant (delete it or pass FRESH=1 to re-export).
set -euo pipefail

PAIR="${1:?pair required (e.g. dapper-mongodb)}"
VARIANT="${2:-full}"
MODEL="${3:-}"
EFFORT="${4:-high}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"   # services/orchestrator
OUT_ROOT="$ROOT/evaluation/manual-eval/wwi"

cd "$ROOT"

# ---- 1. export (reuse newest existing export unless FRESH=1)
EXPORT_DIR="$(ls -dt "$OUT_ROOT/${PAIR}__${VARIANT}__"*/ 2>/dev/null | head -1 || true)"
if [[ -z "$EXPORT_DIR" || "${FRESH:-0}" == "1" ]]; then
  echo "== exporting prompt for $PAIR [$VARIANT] (drives the live graph up to the model call)"
  uv run python evaluation/scripts/export_manual_prompts.py --pair "$PAIR" --variant "$VARIANT" \
    --out evaluation/manual-eval --env .env.dev
  EXPORT_DIR="$(ls -dt "$OUT_ROOT/${PAIR}__${VARIANT}__"*/ | head -1)"
fi
EXPORT_DIR="${EXPORT_DIR%/}"
echo "== export: $EXPORT_DIR"

# ---- 2. run Claude Code headless, chat mode (no tools), isolated CWD
PROMPT_FILE="$EXPORT_DIR/.combined-user-prompt.txt"
cat "$EXPORT_DIR/user.txt" > "$PROMPT_FILE"
printf '\n\n' >> "$PROMPT_FILE"
cat "$EXPORT_DIR/adaptation.txt" >> "$PROMPT_FILE"

# TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
# SETTINGS_FILE="/tmp/bare-settings.json"
# CLAUDE_CODE_CREDENTIALS_FILE="$HOME/.claude/.credentials.json"
# TOKEN=$(cat "$CLAUDE_CODE_CREDENTIALS_FILE" | jq -r '.claudeAiOauth.accessToken')
# echo "{\"apiKeyHelper\": \"echo $TOKEN\"}" > "$SETTINGS_FILE"
# chmod 600 "$SETTINGS_FILE"
# CLAUDE_ARGS=(-p --bare --settings "$SETTINGS_FILE" --append-system-prompt-file "$EXPORT_DIR/system.txt" --tools "" --effort "$EFFORT" --permission-mode "auto" --dangerously-skip-permissions --no-chrome)

CLAUDE_ARGS=(-p --safe-mode --append-system-prompt-file "$EXPORT_DIR/system.txt" --tools "" --effort "$EFFORT" --permission-mode "auto" --dangerously-skip-permissions --no-chrome)
[[ -n "$MODEL" ]] && CLAUDE_ARGS+=(--model "$MODEL")

# Per-model capture name: the comparison matrix runs several models against ONE shared export,
# so a fixed capture.md would silently overwrite the previous model's answer.
MODEL_LABEL="${MODEL:-claude-code-default}-${EFFORT}"
CAPTURE="$EXPORT_DIR/capture-claude_code-${MODEL_LABEL}.md"

echo "== running: claude ${CLAUDE_ARGS[*]} (prompt: $(wc -c < "$PROMPT_FILE") bytes) — this spends Claude tokens"
START=$(date +%s)
(cd "$EXPORT_DIR" && ENABLE_CLAUDEAI_MCP_SERVERS=false CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" > "$CAPTURE")
WALL=$(( $(date +%s) - START ))
echo "== captured $(wc -c < "$CAPTURE") bytes in ${WALL}s -> $CAPTURE"

# rm "$SETTINGS_FILE"

# ---- 2b. persist REAL API usage from the Claude Code session transcript (claude -p prints no
# usage, but the transcript under ~/.claude/projects/<munged CWD>/ records the API-reported
# input/cache/output token counts per message id — the 20260709 arm run had to reconstruct these
# forensically; now they are captured at run time). Best-effort: never fails the arm.
USAGE_JSON="$EXPORT_DIR/usage-claude_code-${MODEL_LABEL}.json"
PROJ_DIR="$HOME/.claude/projects/$(echo "$EXPORT_DIR" | sed 's#[/._]#-#g')"
TRANSCRIPT="$(ls -t "$PROJ_DIR"/*.jsonl 2>/dev/null | head -1 || true)"
if [[ -n "$TRANSCRIPT" ]]; then
  # Keep the FULL conversation next to the capture for reproduction/audit (the transcript dir
  # under ~/.claude is private and machine-local; the copy travels with the experiment).
  cp "$TRANSCRIPT" "$EXPORT_DIR/conversation-claude_code-${MODEL_LABEL}.jsonl" \
    && echo "== conversation -> $EXPORT_DIR/conversation-claude_code-${MODEL_LABEL}.jsonl"
  jq -s --arg wall "$WALL" '
    [ .[] | select(.message.usage != null)
      | {id: .message.id, model: .message.model, u: .message.usage} ]
    | unique_by(.id)
    | {wall_clock_generation_s: ($wall|tonumber),
       requests: length,
       model: (.[0].model // null),
       input_tokens: (map(.u.input_tokens) | add),
       cache_creation_input_tokens: (map(.u.cache_creation_input_tokens // 0) | add),
       cache_read_input_tokens: (map(.u.cache_read_input_tokens // 0) | add),
       output_tokens: (map(.u.output_tokens) | add)}' \
    "$TRANSCRIPT" > "$USAGE_JSON" 2>/dev/null \
    && echo "== usage -> $USAGE_JSON: $(cat "$USAGE_JSON" | tr -d '\n')" \
    || echo "== [warn] could not parse usage from $TRANSCRIPT"
else
  echo "== [warn] no Claude Code transcript found under $PROJ_DIR — usage not persisted"
fi

# ---- 3. score with the pipeline's own gauntlet
uv run python evaluation/scripts/score_external.py \
  --capture "$CAPTURE" \
  --pair "$PAIR" --variant "$VARIANT" \
  --approach claude_code --model-label "$MODEL_LABEL" \
  --out evaluation/out/external --pred-root evaluation/predictions --env .env.dev

echo "== done. generation wall clock (Claude side): ${WALL}s"
