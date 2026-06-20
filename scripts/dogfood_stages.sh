# CCER dogfood stage definitions — sourced by scripts/dogfood.sh
# Each stage: ID|COMMIT_MSG|CLAUDE(0=no,1=yes)|HINT|prompt text...

STAGE_COUNT=15

stage_commit_msg() {
  case "$1" in
    0)  echo "chore: add gitignore" ;;
    1)  echo "feat: add expense-cli with add, list, and summary commands" ;;
    2)  echo "test: add pytest coverage for expense-cli commands" ;;
    3)  echo "refactor: split expense-cli into package modules" ;;
    4)  echo "feat: add CSV import and export commands" ;;
    5)  echo "fix: handle corrupt expenses.json and empty lines in summary" ;;
    6)  echo "feat: migrate storage from JSON to SQLite" ;;
    7)  echo 'Revert "feat: migrate storage from JSON to SQLite"' ;;
    8)  echo "feat: add --version flag" ;;
    9)  echo "docs: trailing newline in readme" ;;
    10) echo "" ;;  # audit-only, no commit
    11) echo "docs: fix typo in readme" ;;
    12) echo "feat: add category filter to list command" ;;
    13) echo "fix: exclude empty category from filtered list" ;;
    14) echo "fix: correct category-filtered summary totals" ;;
    *)  return 1 ;;
  esac
}

stage_uses_claude() {
  case "$1" in
    0|7|9|10) echo "0" ;;
    *)        echo "1" ;;
  esac
}

stage_hint() {
  case "$1" in
    0)  echo "No Claude — script commits .gitignore only" ;;
    3)  echo "Headless: dogfood.sh run 3 uses CLAUDE_OPUS_MODEL. Interactive: run /model first." ;;
    7)  echo "No Claude — script runs git revert HEAD" ;;
    9)  echo "No Claude — dogfood.sh appends README newline (fully automatic)" ;;
    10) echo "No Claude — script replays ccer audit on stage 5 fix commit" ;;
    11) echo "Uses CLAUDE_OPUS_MODEL on a one-word README fix — tests Opus overspend penalty" ;;
    12) echo "Ships a category filter with a deliberate bug still in the code" ;;
    13) echo "First fix commit — partial; summary still wrong for filtered categories" ;;
    14) echo "Second fix commit — fully resolves the category filter bug" ;;
    *)  echo "Automated: dogfood.sh run N. Manual: paste prompt into Claude Code, then dogfood.sh done N" ;;
  esac
}

# Model for claude -p (stages 3 and 11 use Opus)
stage_model() {
  local stage="$1"
  local default="${CLAUDE_MODEL:-claude-sonnet-4-6}"
  local opus="${CLAUDE_OPUS_MODEL:-claude-opus-4-6}"
  case "$stage" in
    3|11) echo "$opus" ;;
    *)  echo "$default" ;;
  esac
}

stage_goal() {
  case "$1" in
    0)  echo "Zero-token / git-only audit" ;;
    1)  echo "Baseline usage + diff correlation" ;;
    2)  echo "Tests touched, efficiency baseline" ;;
    3)  echo "Model breakdown + switch timeline" ;;
    4)  echo "High turn count / tool loops" ;;
    5)  echo "FIX_KEYWORD rework flag" ;;
    6)  echo "ADD_DELETE_SPIKE / file churn" ;;
    7)  echo "REVERT rework flag" ;;
    8)  echo "Time slicing in shared Claude session" ;;
    9)  echo "Commit without Claude (script edits README)" ;;
    10) echo "Historical --commit replay" ;;
    11) echo "Opus overspend penalty on low-output commit" ;;
    12) echo "Introduce bug (category filter shipped broken)" ;;
    13) echo "Follow-up fix 1 of 2 (partial fix, FIX_KEYWORD)" ;;
    14) echo "Follow-up fix 2 of 2 (bug fully fixed, FIX_KEYWORD)" ;;
    *)  echo "" ;;
  esac
}

stage_prompt() {
  case "$1" in
    1) cat <<'EOF'
Build a Python CLI expense tracker called expense-cli in this repo.

Requirements:
- Use argparse and a single module expense_cli.py
- Commands: add <amount> <category> <note>, list, summary
- Store expenses in expenses.json in the current directory
- Include a requirements.txt (stdlib only is fine, file can be empty or comment-only)
- Add a minimal README.md with usage examples

Do not add tests yet. Keep it simple and working.
EOF
    ;;
    2) cat <<'EOF'
Add unit tests for expense-cli using pytest.

- Create tests/test_expense_cli.py
- Test add, list, and summary with a temporary JSON file (use tmp_path fixture)
- Add pytest to requirements.txt
- Make sure tests pass with pytest
EOF
    ;;
    3) cat <<'EOF'
Refactor expense-cli for clarity:
- Split into expense_cli/ package: cli.py, storage.py, models.py
- Keep the same CLI behavior and all tests passing
- Update imports in tests accordingly
EOF
    ;;
    4) cat <<'EOF'
Add a export csv subcommand that writes expenses to stdout as CSV.
Also add import csv from a file path.
Update README and add tests for both commands.
Run the full test suite and fix anything broken.
EOF
    ;;
    5) cat <<'EOF'
There's a bug: summary double-counts expenses when the JSON file has trailing whitespace lines. Fix storage loading to strip empty lines and handle corrupt JSON gracefully with a clear error message. Add a test for the corrupt file case.
EOF
    ;;
    6) cat <<'EOF'
Replace the JSON storage backend with SQLite in expenses.db.
Use a single expenses table. Keep the same CLI interface.
Migrate tests to use an in-memory or temp-file database.
Delete storage.py JSON logic entirely and rewrite it.
EOF
    ;;
    8) cat <<'EOF'
Add a --version flag to the CLI that prints expense-cli 0.1.0.
EOF
    ;;
    11) cat <<'EOF'
README.md misspells "tracker" as "traker" in one place. Fix only that single typo — change traker to tracker. Do not edit any other file or line.
EOF
    ;;
    12) cat <<'EOF'
Add an optional --category FILTER argument to the list command (e.g. expense-cli list --category food).

Implement the filter but leave this bug in place on purpose: when --category is set, expenses whose category is an empty string are still included in the output.

Add happy-path tests only (filtered list returns matching category). Do not add tests for empty category yet. Update README with the new flag.
EOF
    ;;
    13) cat <<'EOF'
Fix the category filter bug: when --category is set, expenses with an empty category string must be excluded from list output.

Do NOT fix summary yet — summary should still show totals for ALL expenses even when the user just filtered list by category. That summary bug is intentional for the next commit.

Add a test proving empty-category rows are excluded from filtered list. Run pytest.
EOF
    ;;
    14) cat <<'EOF'
Fix the remaining category filter bug: add --category FILTER to the summary command so summary totals only include expenses in that category.

When summary is run with --category food, total amount and count must match only food expenses.

Add tests for category-filtered summary. Run the full test suite and fix failures.
EOF
    ;;
    *)  echo "" ;;
  esac
}

stage_expect() {
  case "$1" in
    0)  echo "0 tokens; git diff present; efficiency High" ;;
    1)  echo "Non-zero tokens; no rework flags; diff shows new files" ;;
    2)  echo "Lower tokens than stage 1; tests mentioned in report" ;;
    3)  echo "2+ models in breakdown; switch timeline entry" ;;
    4)  echo "Higher turn count; tool loop evidence" ;;
    5)  echo "FIX_KEYWORD rework flag; Medium/Low efficiency" ;;
    6)  echo "ADD_DELETE_SPIKE or FILE_CHURN on rewritten files" ;;
    7)  echo "REVERT flag; Low efficiency" ;;
    8)  echo "Token total much smaller than early stages (time slice)" ;;
    9)  echo "~0 tokens; tiny diff; efficiency High" ;;
    10) echo "Same report as original stage 5 audit" ;;
    11) echo "Opus >40% spend on tiny diff; efficiency penalty or warning in report" ;;
    12) echo "No rework flag; new feature commit with hidden bug; tokens for new code" ;;
    13) echo "FIX_KEYWORD; partial fix; efficiency Medium/Low (paying to fix own bug)" ;;
    14) echo "FIX_KEYWORD; bug resolved; compare token spend vs stage 12+13 total" ;;
    *)  echo "" ;;
  esac
}
