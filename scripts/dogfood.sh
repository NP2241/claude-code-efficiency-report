#!/usr/bin/env bash
# CCER dogfood conductor — runs Claude Code headless (claude -p), git commits, ccer audit.
#
# Primary workflow (automated — Cursor agent or you run from terminal):
#   ./scripts/dogfood.sh init
#   ./scripts/dogfood.sh run          # current stage: claude -p → commit → audit
#   ./scripts/dogfood.sh run-all      # stages 0–10 unattended
#
# Manual fallback (interactive Claude Code):
#   ./scripts/dogfood.sh show → paste into claude → ./scripts/dogfood.sh done

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=dogfood_stages.sh
source "$SCRIPT_DIR/dogfood_stages.sh"

TEST_DIR="${CCER_TEST_DIR:-$HOME/Downloads/claude-expense-tracker}"
CCER_GIT_REMOTE="${CCER_GIT_REMOTE:-git@github.com:NP2241/claude-expense-tracker.git}"
STATE_FILE="$TEST_DIR/.ccer/dogfood-state"
CONTINUE_FLAG_FILE="$TEST_DIR/.ccer/dogfood-claude-started"
SKIP_AUDIT="${SKIP_AUDIT:-0}"
SKIP_CLAUDE="${SKIP_CLAUDE:-0}"
SKIP_PUSH="${SKIP_PUSH:-0}"
MAX_TURNS="${MAX_TURNS:-40}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-4-6}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[dogfood]${NC} $*"; }
warn() { echo -e "${YELLOW}[dogfood]${NC} $*"; }
die()  { echo -e "${RED:-}${1}${NC:-}" >&2; exit 1; }

read_state() {
  if [[ -f "$STATE_FILE" ]]; then
    cat "$STATE_FILE"
  else
    echo "0"
  fi
}

write_state() {
  mkdir -p "$(dirname "$STATE_FILE")"
  echo "$1" > "$STATE_FILE"
}

require_repo() {
  [[ -d "$TEST_DIR/.git" ]] || die "No repo at $TEST_DIR — run: ./scripts/dogfood.sh init"
}

audit() {
  [[ "$SKIP_AUDIT" == "1" ]] && { warn "Skipping ccer audit (SKIP_AUDIT=1)"; return 0; }
  if ! command -v ccer >/dev/null 2>&1; then
    warn "ccer not installed — run: pip install -e $ROOT"
    return 0
  fi
  (cd "$TEST_DIR" && ccer audit) || warn "ccer audit failed"
}

prep_stage() {
  local stage="$1"
  case "$stage" in
    11)
      local readme="$TEST_DIR/README.md"
      [[ -f "$readme" ]] || return 0
      if ! grep -q 'traker' "$readme"; then
        sed -i '' 's/tracker/traker/' "$readme" 2>/dev/null || \
          sed -i 's/tracker/traker/' "$readme" 2>/dev/null || true
      fi
      ;;
  esac
}

commit_stage_files() {
  local stage="$1"
  case "$stage" in
    0)
      echo "expenses.json" >> "$TEST_DIR/.gitignore"
      echo "__pycache__/" >> "$TEST_DIR/.gitignore"
      echo "*.pyc" >> "$TEST_DIR/.gitignore"
      echo ".ccer/" >> "$TEST_DIR/.gitignore"
      ;;
    9)
      echo "" >> "$TEST_DIR/README.md"
      ;;
  esac
}

git_commit() {
  local msg="$1"
  cd "$TEST_DIR"
  if [[ -f .gitignore ]] && ! grep -q '^\.ccer/' .gitignore 2>/dev/null; then
    echo ".ccer/" >> .gitignore
  fi
  git add -A
  git reset HEAD -- .ccer/ 2>/dev/null || true
  if git diff --cached --quiet; then
    warn "Nothing to commit — Claude may have already committed; continuing"
    return 0
  fi
  git -c user.email="${CCER_GIT_EMAIL:-ccer-test@local}" \
      -c user.name="${CCER_GIT_NAME:-CCER Test}" \
      commit -m "$msg"
}

git_push() {
  [[ "$SKIP_PUSH" == "1" ]] && { warn "Skipping git push (SKIP_PUSH=1)"; return 0; }
  cd "$TEST_DIR"
  local branch remote
  branch="$(git branch --show-current)"
  remote="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -z "$remote" ]]; then
    warn "No origin remote — set CCER_GIT_REMOTE and re-run init"
    return 0
  fi
  log "Pushing to origin ($branch)"
  if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
    git push
  else
    git push -u origin "$branch"
  fi
}

ensure_remote() {
  cd "$TEST_DIR"
  if git remote get-url origin >/dev/null 2>&1; then
    local current
    current="$(git remote get-url origin)"
    if [[ "$current" != "$CCER_GIT_REMOTE" ]]; then
      log "Updating origin: $CCER_GIT_REMOTE"
      git remote set-url origin "$CCER_GIT_REMOTE"
    fi
  else
    log "Adding origin: $CCER_GIT_REMOTE"
    git remote add origin "$CCER_GIT_REMOTE"
  fi
}

finish_stage() {
  local stage="$1"
  local msg
  msg="$(stage_commit_msg "$stage")" || die "Unknown stage: $stage"

  case "$stage" in
    7)
      log "Running git revert (stage 7)"
      cd "$TEST_DIR"
      mkdir -p .ccer
      if [[ -f .gitignore ]] && ! grep -q '^\.ccer/' .gitignore 2>/dev/null; then
        echo ".ccer/" >> .gitignore
      fi
      git rm -rf --cached .ccer 2>/dev/null || true
      git add .gitignore
      git -c user.email="${CCER_GIT_EMAIL:-ccer-test@local}" \
          -c user.name="${CCER_GIT_NAME:-CCER Test}" \
          commit -m "chore: gitignore .ccer metadata" 2>/dev/null || true
      local revert_sha
      revert_sha=$(git log -1 --format="%H" --grep="replace JSON storage with SQLite")
      [[ -z "$revert_sha" ]] && revert_sha=$(git log -1 --format="%H" --grep="SQLite backend")
      [[ -z "$revert_sha" ]] && revert_sha="HEAD~1"
      log "Reverting ${revert_sha:0:8} (SQLite migration)"
      git revert "$revert_sha" --no-edit
      git_push
      ;;
    10)
      local sha
      sha=$(cd "$TEST_DIR" && git log --oneline --grep="fix: handle corrupt" --format="%H" -1 2>/dev/null || true)
      if [[ -z "$sha" ]]; then
        warn "Stage 5 fix commit not found — skipping historical audit"
        return 0
      fi
      log "Historical audit: ccer audit --commit ${sha:0:8}"
      if command -v ccer >/dev/null 2>&1; then
        (cd "$TEST_DIR" && ccer audit --commit "$sha") || warn "Historical audit failed"
      fi
      return 0
      ;;
    *)
      commit_stage_files "$stage"
      log "Committing: $msg"
      git_commit "$msg"
      git_push
      ;;
  esac

  audit
}

print_stage() {
  local stage="$1"
  local uses_claude hint goal expect prompt msg

  uses_claude="$(stage_uses_claude "$stage")"
  hint="$(stage_hint "$stage")"
  goal="$(stage_goal "$stage")"
  expect="$(stage_expect "$stage")"
  prompt="$(stage_prompt "$stage")"
  msg="$(stage_commit_msg "$stage" 2>/dev/null || echo "(no commit)")"

  echo ""
  echo -e "${BOLD}══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD} Stage $stage${NC} — $goal"
  echo -e "${BOLD}══════════════════════════════════════════════════════════════${NC}"
  echo ""
  echo -e "${CYAN}Hint:${NC} $hint"
  echo -e "${CYAN}Commit:${NC} $msg"
  echo -e "${CYAN}Expect in report:${NC} $expect"
  echo ""

  if [[ "$uses_claude" == "1" && -n "$prompt" ]]; then
    echo -e "${BOLD}── Prompt (claude -p / interactive) ──${NC}"
    echo ""
    echo "$prompt"
    echo ""
    echo -e "${BOLD}────────────────────────────${NC}"
    echo ""
    echo "Automated:  ./scripts/dogfood.sh run $stage"
    echo "Manual:     paste into Claude Code, then  ./scripts/dogfood.sh done $stage"
  elif [[ "$stage" == "10" ]]; then
    echo "No prompt. Run:  ./scripts/dogfood.sh done 10"
  else
    echo "No Claude prompt for this stage."
    echo "Run:  ./scripts/dogfood.sh done $stage"
  fi
}

cmd_init() {
  log "Test repo: $TEST_DIR"
  log "Remote:    $CCER_GIT_REMOTE"

  if [[ -d "$TEST_DIR/.git" ]]; then
    log "Existing repo found — ensuring remote and branch"
    ensure_remote
  elif [[ -d "$TEST_DIR" ]]; then
    cd "$TEST_DIR"
    git init -b main -q
    ensure_remote
  else
    if git clone "$CCER_GIT_REMOTE" "$TEST_DIR" 2>/dev/null; then
      log "Cloned from GitHub"
    else
      log "Clone failed or empty remote — initializing locally"
      mkdir -p "$TEST_DIR"
      cd "$TEST_DIR"
      git init -b main -q
      ensure_remote
    fi
  fi

  cd "$TEST_DIR"
  if [[ ! -f README.md ]]; then
    echo "# claude-expense-tracker" > README.md
    echo "" >> README.md
    echo "Python CLI expense tracker — CCER dogfood demo repo." >> README.md
    git add README.md
    git -c user.email="${CCER_GIT_EMAIL:-ccer-test@local}" \
        -c user.name="${CCER_GIT_NAME:-CCER Test}" \
        commit -m "chore: init repo" 2>/dev/null || true
    git_push || warn "Initial push failed — check SSH (git-repo-operator skill)"
  fi

  write_state "0"
  rm -f "$CONTINUE_FLAG_FILE"
  log "Repo ready. Next steps:"
  echo "  set -a && source .env && set +a    # from claude-code-efficiency-report"
  echo "  ./scripts/dogfood.sh run           # claude -p → commit → push → audit"
  echo "  ./scripts/dogfood.sh run-all       # full playbook"
  echo ""
  encoded="-$(echo "$TEST_DIR" | sed 's|^/||' | tr '/' '-')"
  log "Transcripts: ~/.claude/projects/${encoded}/"
  log "GitHub:      https://github.com/NP2241/claude-expense-tracker"
}

invoke_claude() {
  local stage="$1"
  local prompt model
  prompt="$(stage_prompt "$stage")"
  [[ -n "$prompt" ]] || return 0

  if [[ "$SKIP_CLAUDE" == "1" ]]; then
    warn "Skipping claude -p (SKIP_CLAUDE=1)"
    return 0
  fi

  command -v claude >/dev/null 2>&1 || die "claude CLI not found — install Claude Code"

  model="$(stage_model "$stage")"
  local -a args=(
    claude -p "$prompt"
    --bare
    --model "$model"
    --max-turns "$MAX_TURNS"
    --output-format json
    --permission-mode acceptEdits
    --allowedTools "Read,Edit,Write,Bash,Glob,Grep"
  )
  if [[ -f "$CONTINUE_FLAG_FILE" ]]; then
    args+=(--continue)
  fi

  log "claude -p (stage $stage, model $model) in $TEST_DIR"
  mkdir -p "$(dirname "$CONTINUE_FLAG_FILE")"
  (cd "$TEST_DIR" && "${args[@]}" >"$TEST_DIR/.ccer/claude-last.json" 2>"$TEST_DIR/.ccer/claude-last.err") || {
    warn "claude exited non-zero — see $TEST_DIR/.ccer/claude-last.err"
    cat "$TEST_DIR/.ccer/claude-last.err" >&2
    return 1
  }
  touch "$CONTINUE_FLAG_FILE"
}

cmd_run() {
  require_repo
  local stage="${1:-$(read_state)}"
  print_stage "$stage"
  prep_stage "$stage"
  if [[ "$(stage_uses_claude "$stage")" == "1" ]]; then
    invoke_claude "$stage"
  fi
  cmd_done "$stage"
}

cmd_run_all() {
  require_repo
  local start="${1:-$(read_state)}"
  local s
  for ((s=start; s<=14; s++)); do
    log "========== Running stage $s =========="
    write_state "$s"
    cmd_run "$s"
  done
  log "All stages complete."
  if command -v ccer >/dev/null 2>&1; then
    log "Generating full scenario report: ccer scenario"
    (cd "$TEST_DIR" && ccer scenario) || warn "ccer scenario failed"
  fi
}

cmd_show() {
  require_repo
  local stage="${1:-$(read_state)}"
  print_stage "$stage"
}

cmd_done() {
  require_repo
  local stage="${1:-$(read_state)}"
  finish_stage "$stage"
  local next=$((stage + 1))
  if [[ "$next" -le 14 ]]; then
    write_state "$next"
    log "Stage $stage complete. Next: stage $next"
    print_stage "$next"
  else
    write_state "done"
    log "All stages complete."
    (cd "$TEST_DIR" && git log --oneline)
    if command -v ccer >/dev/null 2>&1; then
      (cd "$TEST_DIR" && ccer scenario) || warn "ccer scenario failed"
    fi
    [[ -d "$TEST_DIR/.ccer/reports" ]] && ls -la "$TEST_DIR/.ccer/reports/"
  fi
}

cmd_prompt() {
  # Machine-readable: just the prompt text (for Cursor to relay)
  local stage="${1:?Usage: dogfood.sh prompt <stage>}"
  stage_prompt "$stage"
}

cmd_status() {
  require_repo
  local state
  state="$(read_state)"
  log "Test repo: $TEST_DIR"
  log "Current stage: $state"
  echo ""
  (cd "$TEST_DIR" && git log --oneline -5 2>/dev/null) || true
}

cmd_reset() {
  write_state "0"
  log "Reset to stage 0 (repo unchanged)"
}

usage() {
  cat <<EOF
Usage: ./scripts/dogfood.sh <command> [stage]

Commands:
  init              Clone/init ~/claude-expense-tracker, set origin, reset to stage 0
  run [N]           claude -p → commit → push → audit for stage N (default: current)
  run-all [N]       Run stages N through 10 unattended
  show [N]          Print stage N prompt + hints (default: current stage)
  done [N]          Commit → push → audit only — skip claude -p
  prompt N          Print prompt only
  status            Show current stage and recent commits
  reset             Reset stage counter to 0 without touching repo

Env:
  CCER_TEST_DIR       Test repo path (default: ~/claude-expense-tracker)
  CCER_GIT_REMOTE     origin URL (default: git@github.com:NP2241/claude-expense-tracker.git)
  ANTHROPIC_API_KEY   Required for claude -p --bare (or existing OAuth)
  CLAUDE_MODEL        Default model (default: claude-sonnet-4-6)
  CLAUDE_OPUS_MODEL   Stage 3 model switch (default: claude-opus-4-6)
  MAX_TURNS           Cap per stage (default: 40)
  SKIP_CLAUDE=1       Git/push/audit only, no claude -p
  SKIP_AUDIT=1        Skip ccer audit (while tool is WIP)
  SKIP_PUSH=1         Commit locally only, no push

Workflow (automated — same transcripts as interactive Claude Code):
  ./scripts/dogfood.sh init && ./scripts/dogfood.sh run-all

Workflow (manual interactive Claude Code):
  ./scripts/dogfood.sh show → paste into claude → ./scripts/dogfood.sh done
EOF
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    init)    cmd_init "$@" ;;
    run)     cmd_run "$@" ;;
    run-all) cmd_run_all "$@" ;;
    show)    cmd_show "$@" ;;
    done)    cmd_done "$@" ;;
    prompt)  cmd_prompt "$@" ;;
    status)  cmd_status "$@" ;;
    reset)   cmd_reset "$@" ;;
    *)       usage ;;
  esac
}

main "$@"
