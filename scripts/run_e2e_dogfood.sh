#!/usr/bin/env bash
# Run the full CCER dogfood playbook from test.md using Claude Code headless.
#
# Requires: git, claude CLI (2.x), ANTHROPIC_API_KEY or Claude auth, ccer (pip install -e .)
#
# Usage:
#   export ANTHROPIC_API_KEY=sk-...
#   ./scripts/run_e2e_dogfood.sh
#
# Options (env vars):
#   CCER_TEST_DIR     — repo path (default: /tmp/ccer-test-app-<pid>)
#   CLAUDE_MODEL      — default model (default: claude-sonnet-4-6)
#   CLAUDE_OPUS_MODEL — model for stage 3 switch test (default: claude-opus-4-6)
#   SKIP_CLAUDE       — 1 = git-only stages only (0, 9); no API spend
#   SKIP_AUDIT        — 1 = skip ccer audit (useful while ccer is still WIP)
#   DRY_RUN           — 1 = print commands without running claude/commits
#   MAX_TURNS         — cap per stage (default: 40)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="${CCER_TEST_DIR:-/tmp/ccer-test-app-$$}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-4-6}"
CLAUDE_OPUS_MODEL="${CLAUDE_OPUS_MODEL:-claude-opus-4-6}"
SKIP_CLAUDE="${SKIP_CLAUDE:-0}"
SKIP_AUDIT="${SKIP_AUDIT:-0}"
DRY_RUN="${DRY_RUN:-0}"
MAX_TURNS="${MAX_TURNS:-40}"
CONTINUE_FLAG=""  # set after first claude call

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[ccer-e2e]${NC} $*"; }
warn() { echo -e "${YELLOW}[ccer-e2e]${NC} $*"; }
die()  { echo -e "${RED}[ccer-e2e]${NC} $*" >&2; exit 1; }

run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

require_bin() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

audit() {
  [[ "$SKIP_AUDIT" == "1" ]] && { warn "Skipping ccer audit (SKIP_AUDIT=1)"; return 0; }
  require_bin ccer
  log "Running: ccer audit"
  run_cmd ccer audit || warn "ccer audit failed (tool may still be WIP)"
}

commit() {
  local msg="$1"
  log "Commit: $msg"
  run_cmd git add -A
  run_cmd git -c user.email="ccer-e2e@test.local" -c user.name="CCER E2E" \
    commit -m "$msg" --allow-empty
  audit
}

run_claude() {
  local prompt="$1"
  local model="${2:-$CLAUDE_MODEL}"

  if [[ "$SKIP_CLAUDE" == "1" ]]; then
    warn "Skipping Claude (SKIP_CLAUDE=1): ${prompt:0:60}..."
    return 0
  fi

  require_bin claude

  local -a args=(
    claude -p "$prompt"
    --bare
    --model "$model"
    --max-turns "$MAX_TURNS"
    --output-format json
    --permission-mode acceptEdits
    --allowedTools "Read,Edit,Write,Bash,Glob,Grep"
  )
  if [[ -n "$CONTINUE_FLAG" ]]; then
    args+=(--continue)
  fi

  log "Claude ($model): ${prompt:0:72}..."
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] ${args[*]}"
  else
    # shellcheck disable=SC2068
    "${args[@]}" >/tmp/ccer-e2e-claude-last.json 2>/tmp/ccer-e2e-claude-last.err || {
      warn "Claude exited non-zero; see /tmp/ccer-e2e-claude-last.err"
      cat /tmp/ccer-e2e-claude-last.err >&2
    }
    CONTINUE_FLAG=1
  fi
}

setup_repo() {
  log "Test repo: $TEST_DIR"
  if [[ "$DRY_RUN" != "1" ]]; then
    rm -rf "$TEST_DIR"
    mkdir -p "$TEST_DIR"
  fi
  cd "$TEST_DIR"

  run_cmd git init -q
  run_cmd git -c user.email="ccer-e2e@test.local" -c user.name="CCER E2E" \
    commit --allow-empty -m "chore: init repo" 2>/dev/null || true
  echo "# CCER test app" > README.md
  run_cmd git add README.md
  run_cmd git -c user.email="ccer-e2e@test.local" -c user.name="CCER E2E" \
    commit -m "chore: init repo"
}

stage_0() {
  log "=== Stage 0: git-only (no Claude) ==="
  echo "expense-cli/" >> .gitignore
  commit "chore: add gitignore"
}

stage_1() {
  log "=== Stage 1: scaffold expense-cli ==="
  run_claude "Build a Python CLI expense tracker called expense-cli in this repo.

Requirements:
- Use argparse and a single module expense_cli.py
- Commands: add <amount> <category> <note>, list, summary
- Store expenses in expenses.json in the current directory
- Include requirements.txt (stdlib only is fine)
- Update README.md with usage examples
Do not add tests yet. Keep it simple and working."
  commit "feat: add expense-cli with add, list, and summary commands"
}

stage_2() {
  log "=== Stage 2: pytest coverage ==="
  run_claude "Add unit tests for expense-cli using pytest.
- Create tests/test_expense_cli.py
- Test add, list, and summary with tmp_path fixture
- Add pytest to requirements.txt
- Run pytest and fix failures before finishing"
  commit "test: add pytest coverage for expense-cli commands"
}

stage_3() {
  log "=== Stage 3: refactor (Opus model switch) ==="
  run_claude "Refactor expense-cli for clarity:
- Split into expense_cli/ package: cli.py, storage.py, models.py
- Keep the same CLI behavior and all tests passing
- Update test imports accordingly" "$CLAUDE_OPUS_MODEL"
  commit "refactor: split expense-cli into package modules"
}

stage_4() {
  log "=== Stage 4: CSV import/export (tool loops) ==="
  run_claude "Add export csv subcommand (stdout) and import csv from a file path.
Update README and add tests. Run the full test suite and fix anything broken."
  commit "feat: add CSV import and export commands"
}

stage_5() {
  log "=== Stage 5: fix commit (FIX_KEYWORD) ==="
  run_claude "Fix a bug: summary double-counts when expenses.json has trailing whitespace.
Make storage strip empty lines and handle corrupt JSON with a clear error.
Add a test for corrupt file case."
  commit "fix: handle corrupt expenses.json and empty lines in summary"
}

stage_6() {
  log "=== Stage 6: SQLite migration (churn) ==="
  run_claude "Replace JSON storage with SQLite in expenses.db.
Single expenses table. Same CLI interface. Rewrite storage module and update tests.
Delete old JSON storage logic."
  commit "feat: migrate storage from JSON to SQLite"
}

stage_7() {
  log "=== Stage 7: revert (REVERT) ==="
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] git revert HEAD --no-edit"
  else
    git revert HEAD --no-edit
    audit
  fi
}

stage_8() {
  log "=== Stage 8: time slice (same session, small commit) ==="
  run_claude "Add a --version flag to the CLI that prints expense-cli 0.1.0"
  commit "feat: add --version flag"
}

stage_9() {
  log "=== Stage 9: commit without Claude ==="
  echo "" >> README.md
  commit "docs: trailing newline in readme"
}

stage_10() {
  log "=== Stage 10: historical audit ==="
  if [[ "$SKIP_AUDIT" == "1" ]]; then
    warn "Skipping historical audit"
    return 0
  fi
  local sha
  sha=$(git log --oneline --grep="fix: handle corrupt" --format="%H" -1 2>/dev/null || true)
  if [[ -z "$sha" ]]; then
    warn "Could not find stage 5 commit SHA; skipping --commit replay"
    return 0
  fi
  log "Replay audit for fix commit: ${sha:0:8}"
  run_cmd ccer audit --commit "$sha" || warn "Historical audit failed"
}

summary() {
  log "=== Done ==="
  log "Repo: $TEST_DIR"
  log "Commits:"
  git log --oneline 2>/dev/null || true
  if [[ -d "$TEST_DIR/.ccer/reports" ]]; then
    log "Reports: $TEST_DIR/.ccer/reports/"
    ls -la "$TEST_DIR/.ccer/reports/" 2>/dev/null || true
  fi
  local encoded
  encoded="-$(echo "$TEST_DIR" | sed 's|^/||' | tr '/' '-')"
  log "Expected Claude transcripts: ~/.claude/projects/${encoded}/"
}

main() {
  require_bin git
  if [[ "$SKIP_CLAUDE" != "1" ]]; then
    require_bin claude
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]] && [[ "$DRY_RUN" != "1" ]]; then
      warn "ANTHROPIC_API_KEY not set — claude may use OAuth from keychain instead"
    fi
  fi

  setup_repo
  stage_0
  stage_1
  stage_2
  stage_3
  stage_4
  stage_5
  stage_6
  stage_7
  stage_8
  stage_9
  stage_10
  summary
}

main "$@"
