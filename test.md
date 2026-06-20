# CCER End-to-End Test Playbook

Test **Claude Code Efficiency Report** (`ccer audit`) against a real GitHub repo built with Claude Code. Each stage commits, pushes, and generates an audit report.

---

## Test repository

| | |
|---|---|
| **Local folder** | `~/Downloads/claude-expense-tracker` |
| **GitHub** | [NP2241/claude-expense-tracker](https://github.com/NP2241/claude-expense-tracker) |
| **Remote** | `git@github.com:NP2241/claude-expense-tracker.git` |
| **What gets built** | A Python CLI expense tracker, stage by stage |

---

## Quick start

### 1. Set up this project

```bash
cd ~/Downloads/claude-code-efficiency-report
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Add your Anthropic API key to `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Load it in your shell:

```bash
set -a && source .env && set +a
```

### 2. Test the GitHub connection (do this first)

Before running any dogfood stages, confirm you can push to the remote. Use the **git-repo-operator** skill for SSH setup if needed.

```bash
# Load SSH key (git-repo-operator skill)
ssh-add ~/.ssh/cursor_git_key
ssh -T git@github.com

# Repo should already exist at ~/Downloads/claude-expense-tracker
cd ~/Downloads/claude-expense-tracker
git remote -v
git status
```

Connection test PR (empty commit, no app code):

- Branch `chore/test-connection` is pushed to GitHub
- Open the PR: https://github.com/NP2241/claude-expense-tracker/pull/new/chore/test-connection
- Title: `chore: test GitHub connection` — merge or close it; it's only to verify access

If `gh` is logged in, you can create the PR from the terminal instead:

```bash
gh auth login
gh pr create --title "chore: test GitHub connection" \
  --body "Verify SSH push before CCER dogfood test."
```

**Stop here if push fails.** Fix SSH with git-repo-operator before continuing.

### 3. Run the dogfood test

```bash
cd ~/Downloads/claude-code-efficiency-report
chmod +x scripts/dogfood.sh
./scripts/dogfood.sh init
./scripts/dogfood.sh run          # one stage at a time
# or
./scripts/dogfood.sh run-all      # all stages 0–14
```

Each stage: Claude builds code → commit → push to GitHub → `ccer audit`.

**You don't run the stages yourself.** Ask Cursor: *"run the dogfood test"* or *"run the next stage"* — the agent runs `./scripts/dogfood.sh`, drives Claude via `claude -p`, and uses **git-repo-operator** for git/SSH. Your only one-time setup is `.env` + SSH.

### Who does what

| Step | Who |
|---|---|
| Load API key from `.env` | Cursor agent |
| SSH + git push | Cursor agent (git-repo-operator skill) |
| Run Claude prompts (`claude -p`) | Cursor agent via `dogfood.sh run` |
| Commit + push each stage | `dogfood.sh` (automatic) |
| Stage 0 gitignore, stage 9 README newline, stage 7 revert | `dogfood.sh` (automatic — **not you**) |
| `ccer audit` after each commit | `dogfood.sh` (automatic) |
| Review reports / fix failures | Cursor agent (on request) |

**You:** add API key to `.env`, say "go."

---

## Git operations: use the **git-repo-operator** skill

All commits and pushes during this test must go through the **git-repo-operator** skill. Cursor agents running the dogfood test should **read and follow that skill** for every git operation — SSH setup, commit, push, and remote verification.

**When to use it:**

- First-time setup (SSH key load, `git remote -v`, initial push)
- Any manual commit/push outside `dogfood.sh`
- Recovering from push failures (`Permission denied (publickey)`)
- Verifying branch upstream after each stage

**Skill preflight (agent runs this before pushing):**

```bash
pwd
git status --short --branch
git remote -v
ssh-add -l
ssh -T git@github.com
```

SSH key path (from skill): `/Users/neilpendyala/Downloads/agent_items/git_keys/id_ed25519_github`

**Per-stage push flow (what `dogfood.sh` does automatically):**

```bash
git add -A
git commit -m "<stage message>"
git push -u origin main    # first push; thereafter git push
ccer audit
```

If push fails, the Cursor agent should **stop and use git-repo-operator** to fix SSH/auth before continuing — do not skip pushes; the remote history is part of the demo.

---

## Before you start

### 1. Install CCER

```bash
cd /path/to/claude-code-efficiency-report
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Prerequisites

| Requirement | Notes |
|---|---|
| `claude` CLI | Claude Code 2.x (`claude --version`) |
| `ANTHROPIC_API_KEY` | In `.env` — pay-as-you-go Console key (no subscription required) |
| GitHub SSH | git-repo-operator skill — push to `NP2241/claude-expense-tracker` |
| `git` | Test repo at `~/Downloads/claude-expense-tracker` |

### 3. Init the test project

```bash
./scripts/dogfood.sh init
```

This will:

1. Clone `git@github.com:NP2241/claude-expense-tracker.git` into `~/Downloads/claude-expense-tracker` (or init locally if empty)
2. Set `origin` to the remote above
3. Create initial commit + push (uses SSH — follow git-repo-operator if push fails)
4. Reset stage counter to 0

Claude Code transcripts land at:

```
~/.claude/projects/-Users-<you>-Downloads-claude-expense-tracker/
```

### 4. How `claude -p` maps to CCER

| | Interactive `claude` | Headless `claude -p` |
|---|---|---|
| Transcript location | `~/.claude/projects/...` | Same |
| JSONL schema (`requestId`, `usage`, `model`) | ✅ | ✅ |
| Commit time-slicing | ✅ | ✅ |
| Session continuity | one terminal session | `--continue` across stages |
| Model switch (stage 3) | `/model` in UI | `--model` flag (automatic in script) |
| Remote push | manual or dogfood.sh | automatic each stage |

### 5. What to check after every audit

| Section | What you're validating |
|---|---|
| Usage & cost | Token totals, estimated cost, session count |
| Model breakdown | Per-model token split (stage 3+) |
| Switch timeline | Model changes with timestamps |
| Work completed | Files/themes match the commit |
| Git evidence | Correct SHA, diff stat, commit message |
| Rework analysis | Flags fire (or don't) as expected |
| Efficiency score | High / Medium / Low with reasoning |
| Budget recommendation | Sensible one-liner for managers |
| **GitHub** | Commit visible at github.com/NP2241/claude-expense-tracker |

### 6. Env toggles

```bash
set -a && source .env && set +a          # load API key

SKIP_AUDIT=1 ./scripts/dogfood.sh run    # skip ccer while WIP
SKIP_CLAUDE=1 ./scripts/dogfood.sh run 0 # git/push/audit only
SKIP_PUSH=1 ./scripts/dogfood.sh run     # commit locally, no push (not for demo)
CLAUDE_OPUS_MODEL=claude-opus-4-6        # stage 3 switch model
MAX_TURNS=40
CCER_TEST_DIR=~/Downloads/claude-expense-tracker   # default
CCER_GIT_REMOTE=git@github.com:NP2241/claude-expense-tracker.git
```

---

## The build target

Claude builds a small **Python CLI expense tracker** in **claude-expense-tracker**:

- JSON file storage → later SQLite → revert
- Add / list / summarize commands
- Unit tests
- A deliberate rework arc (fix, churn, revert)

---

## Stages

Each stage: **`claude -p` (if applicable) → commit → push → audit**. GitHub should show a new commit after every stage.

---

### Stage 0 — Baseline (no Claude usage)

**Goal:** Git-only audit, zero tokens.

```bash
./scripts/dogfood.sh run 0
```

**Expected:** Git diff present; ~0 tokens; efficiency **High**; commit on GitHub.

---

### Stage 1 — Scaffold

**Goal:** First commit with Claude usage; baseline token + diff correlation.

```bash
./scripts/dogfood.sh run 1
```

**Prompt** (handled automatically):

> Build a Python CLI expense tracker called `expense-cli` in this repo.
> - `argparse`, single module `expense_cli.py`
> - Commands: `add`, `list`, `summary`
> - Store in `expenses.json`; include `requirements.txt` and `README.md`
> - No tests yet

**Expected:** Non-zero tokens; diff shows new files; no rework flags; efficiency **Medium/High**; pushed to GitHub.

---

### Stage 2 — Tests

**Goal:** Tests touched; moderate diff size.

```bash
./scripts/dogfood.sh run 2
```

**Expected:** Lower tokens than stage 1; tests mentioned in report.

---

### Stage 3 — Model switch

**Goal:** Model breakdown + switch timeline.

```bash
./scripts/dogfood.sh run 3
```

Script uses `CLAUDE_OPUS_MODEL` while stages 1–2 used `CLAUDE_MODEL`. Same session via `--continue`.

**Expected:** 2+ models in breakdown; switch timeline entry.

---

### Stage 4 — Tool loops

**Goal:** High turn count (edit → pytest → fix).

```bash
./scripts/dogfood.sh run 4
```

**Expected:** Higher turn count; same session file, time-sliced per commit.

---

### Stage 5 — FIX_KEYWORD rework

**Goal:** Trigger fix-commit rework rule.

```bash
./scripts/dogfood.sh run 5
```

**Commit message:** `fix: handle corrupt expenses.json and empty lines in summary`

**Expected:** **FIX_KEYWORD** flag; efficiency **Medium/Low**.

---

### Stage 6 — File churn

**Goal:** ADD_DELETE_SPIKE / FILE_CHURN.

```bash
./scripts/dogfood.sh run 6
```

**Expected:** Churn flag on heavily rewritten files; large diff stats.

---

### Stage 7 — Revert

**Goal:** REVERT rework rule.

```bash
./scripts/dogfood.sh run 7
```

Script runs `git revert HEAD --no-edit` and **pushes the revert** to GitHub.

**Expected:** **REVERT** flag; efficiency **Low**; revert commit visible on GitHub.

---

### Stage 8 — Time slicing

**Goal:** Tokens scoped to commit window only, not whole session.

```bash
./scripts/dogfood.sh run 8
```

**Expected:** Small token slice; same session ID, narrower window.

---

### Stage 9 — No Claude (script-only edit)

**Goal:** Commit with zero Claude tokens in the window — simulates a human docs tweak.

**Who does it:** `dogfood.sh` appends a newline to `README.md` automatically. No Claude, no you.

```bash
./scripts/dogfood.sh run 9    # Cursor agent runs this — you do nothing
```

**Expected:** ~0 tokens; tiny diff; efficiency **High**.

---

### Stage 10 — Historical audit

**Goal:** Replay stage 5 with `--commit`.

```bash
./scripts/dogfood.sh run 10
```

**Expected:** Same report as original stage 5 audit (no new commit/push).

---

### Stage 11 — Opus overspend penalty

**Goal:** Flag when Opus spend is high relative to a tiny diff (proposal §6.6 model-aware penalty).

```bash
./scripts/dogfood.sh run 11
```

Script injects a deliberate `traker` typo in README, then runs **Opus** to fix that one word only.

**Expected:** High Opus token cost vs 1-line diff; efficiency penalty or warning; efficiency **Low/Medium**.

---

### Stage 12 — Ship the bug

**Goal:** Push a feature commit that introduces a deliberate bug (no fix yet).

```bash
./scripts/dogfood.sh run 12
```

Adds `list --category` but empty-category rows leak into filtered output.

**Expected:** Normal feature commit; no rework flags; bug present on GitHub.

---

### Stage 13 — Fix attempt 1 of 2

**Goal:** First fix commit — partial; summary still broken.

```bash
./scripts/dogfood.sh run 13
```

**Expected:** **FIX_KEYWORD** flag; list filter fixed; summary bug remains; Medium/Low efficiency.

---

### Stage 14 — Fix attempt 2 of 2

**Goal:** Second fix commit — bug fully resolved.

```bash
./scripts/dogfood.sh run 14
```

**Expected:** **FIX_KEYWORD** flag; category filter works end-to-end; demo shows 3-commit bug arc on GitHub.

---

### Manual — Fallback paths

```bash
cd ~/Downloads/claude-expense-tracker
ccer audit --token-total 50000
ccer audit --usage-file /tmp/usage.jsonl   # when implemented
```

---

### Final report — full scenario trace

After all stages, generate one Markdown report that walks through the entire dogfood test
(stages 0–14, goals, matched commits, tokens, rework flags, rollup):

```bash
cd ~/Downloads/claude-expense-tracker
ccer scenario
```

Output: `.ccer/reports/scenario-claude-expense-tracker-<timestamp>.md`

Per-commit audits remain at `.ccer/reports/<sha>-<timestamp>.md` (Markdown only — no HTML).

`./scripts/dogfood.sh run-all` runs `ccer scenario` automatically at the end.

---

## Command reference

| Command | What it does |
|---|---|
| `./scripts/dogfood.sh init` | Clone/init repo, set remote, push initial commit |
| `./scripts/dogfood.sh run [N]` | `claude -p` → commit → **push** → audit → advance |
| `./scripts/dogfood.sh run-all [N]` | Run stages N–14 unattended; **`ccer scenario`** at end |
| `./scripts/dogfood.sh show [N]` | Print prompt + hints (no execution) |
| `./scripts/dogfood.sh done [N]` | Commit → **push** → audit only |
| `./scripts/dogfood.sh status` | Current stage + recent commits |
| `./scripts/dogfood.sh reset` | Back to stage 0, repo unchanged |

---

## Quick reference cheat sheet

| Stage | Command | Primary CCER feature |
|---|---|---|
| 0 | `run 0` | Zero-token / git-only audit |
| 1 | `run 1` | Baseline usage + diff correlation |
| 2 | `run 2` | Tests touched |
| 3 | `run 3` | Model breakdown + switch timeline |
| 4 | `run 4` | High turn count / tool loops |
| 5 | `run 5` | FIX_KEYWORD rework |
| 6 | `run 6` | ADD_DELETE_SPIKE / file churn |
| 7 | `run 7` | REVERT rework |
| 8 | `run 8` | Time slicing in shared session |
| 9 | `run 9` | Commit without Claude |
| 10 | `run 10` | `--commit` historical replay |
| 11 | `run 11` | Opus overspend penalty on tiny diff |
| 12 | `run 12` | Ship feature with deliberate bug |
| 13 | `run 13` | Follow-up fix 1 of 2 (partial) |
| 14 | `run 14` | Follow-up fix 2 of 2 (complete) |
| Manual | flags only | Fallback `--token-total` / `--usage-file` |
| Final | `ccer scenario` | Full dogfood trace in one `.md` report |

---

## Cursor agent workflow

Cursor runs dogfood stages and **uses the git-repo-operator skill** for all git/SSH operations.

```
You:  Run the CCER dogfood test from stage 1.
Me:   [git-repo-operator: SSH preflight]
      ./scripts/dogfood.sh run 1
      [claude -p → commit → push → ccer audit]
      [verify commit on github.com/NP2241/claude-expense-tracker]
You:  Keep going.
Me:   ./scripts/dogfood.sh run 2
      ...
You:  Run the full test.
Me:   ./scripts/dogfood.sh run-all
```

After all stages:

1. Confirm full commit history on **https://github.com/NP2241/claude-expense-tracker**
2. Run **`ccer scenario`** — one Markdown report tracing all stages
3. Review `.ccer/reports/` against the success checklist

---

## Manual fallback (interactive Claude Code)

```bash
./scripts/dogfood.sh init
cd ~/Downloads/claude-expense-tracker && claude

./scripts/dogfood.sh show
# paste into Claude Code, wait for it to finish
./scripts/dogfood.sh done             # commit → push → audit
```

Use **git-repo-operator skill** if `done` reports a push failure.

---

## Success checklist (PROPOSAL.md §13)

- [ ] `ccer audit` after commit with **no manual usage export**
- [ ] Report uses **real git diff** on HEAD
- [ ] Token cost + **per-model breakdown** + **switch count** (stages 3–4)
- [ ] **FIX_KEYWORD**, **REVERT**, churn/spike flags (stages 5–7)
- [ ] Efficiency tier + budget recommendation on every stage
- [ ] Report readable by a non-technical manager in **< 10 seconds**
- [ ] Stage 8 proves **non-overlapping time slices** in one session
- [ ] **All stages pushed** to `git@github.com:NP2241/claude-expense-tracker.git`

---

## Tips for demo recording

1. Open **https://github.com/NP2241/claude-expense-tracker** alongside the audit report — show commit history + efficiency side by side.
2. Stage 3: model switch in the report.
3. Stage 7: revert on GitHub + Low efficiency in report.
4. Budget **~$10–18** API spend for a full `run-all`; **$20 in Console credits** is enough with buffer.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Permission denied (publickey)` | SSH key not loaded | **git-repo-operator skill** — load key, `ssh -T git@github.com` |
| Push rejected | Remote ahead of local | `git pull --rebase origin main`, then re-push |
| Auth error on `claude -p` | Missing API key | `set -a && source .env && set +a` |
| 0 tokens on Claude-heavy commit | Audit before commit timestamp | Re-run `ccer audit` after commit |
| No transcripts found | Wrong encoded path | Check `~/.claude/projects/-Users-*-Downloads-claude-expense-tracker/` |
| `claude -p` non-zero exit | Turn limit or tool error | See `~/Downloads/claude-expense-tracker/.ccer/claude-last.err` |

---

*Playbook v3 — remote GitHub + git-repo-operator, June 2026*
