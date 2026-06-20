# Claude Code Efficiency Report — Technical Proposal

**Target:** YC demo by **July 27**  
**Demo scope (v0):** `ccer audit` (one command after commit) → auto-read Claude Code logs → git diff on last commit → rework detector → generated report

---

## 1. Problem Statement

Engineering managers need evidence-backed answers to: *"Was this engineer's Claude usage worth it?"* Today that requires manually cross-referencing usage exports, git history, PRs, and CI — slow and subjective.

This tool ingests structured inputs, correlates Claude token spend with git activity, flags rework patterns, and outputs a manager-facing report with drilldown evidence.

---

## 2. Demo vs. Full Product

| Capability | Demo (v0) | Full (post-demo) |
|---|---|---|
| Primary UX | ✅ `ccer audit` from repo root (last commit) | ✅ + CI bot, Slack, scheduled team rollups |
| Claude usage ingestion | ✅ auto-read local Claude Code transcripts | ✅ + Anthropic Admin / Code Analytics API |
| Model tracking | ✅ per-turn model + switch timeline | ✅ + org policy on model mix |
| Git activity analysis | ✅ last commit diff + optional range | ✅ + GitHub API enrichment |
| Diff summary (AI) | ⚠️ rule-based + optional LLM | ✅ full LLM summaries |
| Rework detection | ✅ heuristic rules on commit diff | ✅ + ML patterns across PR history |
| Code quality signals | ⚠️ partial (tests, churn) | ✅ CI + review comments |
| Efficiency score | ✅ High/Med/Low + reasoning | ✅ calibrated scoring |
| Manager report | ✅ Markdown + HTML | ✅ PDF, Slack, email |
| Evidence drilldown | ⚠️ embedded in report | ✅ interactive UI |
| Budget recommendation | ✅ rule-based | ✅ org policy engine |
| Web form / file upload | ⚠️ secondary / fallback | ✅ multi-engineer admin UI |

**Demo principle:** Zero manual usage export on a MacBook. Engineer codes in Claude Code (terminal or editor), commits, runs one command — report appears. Defer auth, multi-tenant, and org APIs until after YC.

---

## 3. Demo UX: Automatic commit audit (Mac)

### 3.1 The workflow we are optimizing for

```
1. Engineer opens Claude Code in Terminal, VS Code, or Cursor (same ~/.claude data)
2. Works on the repo — Claude writes session transcripts locally as they go
3. git commit -m "feat: ..."
4. ccer audit                    # or: auto via post-commit hook
5. Report opens: tokens, models used, diff, rework flags, efficiency score
```

No file upload. No date pickers. No copying token totals from `/usage`.

### 3.2 Where usage data comes from (automatic)

Claude Code already persists **session transcripts as JSONL** on macOS:

```
~/.claude/projects/<encoded-repo-path>/<session-id>.jsonl
~/.claude/projects/<encoded-repo-path>/<session-id>/subagents/*.jsonl
```

The encoded path is derived from the repo's absolute path (e.g. `/Users/dev/my-app` → `-Users-dev-my-app`). Each JSONL line is a structured event with fields we rely on:

| Field | Use |
|---|---|
| `timestamp` | Filter events to the commit time window |
| `sessionId` | Group sessions |
| `cwd` | Match events to the repo being audited |
| `gitBranch` | Optional branch filter |
| `entrypoint` | `cli` vs IDE — show in report |
| `message.model` | Model per assistant turn |
| `message.usage` | `input_tokens`, `output_tokens`, `cache_*` |
| `requestId` | Dedupe multi-line assistant turns (thinking → text → tool_use) |

**Parser rule:** sum usage once per unique `requestId`, not once per JSONL line (Claude logs the same turn multiple times as content blocks stream in).

Optional enrichment (not required for demo):

- `~/.claude/history.jsonl` — prompt history metadata (project + sessionId pointers)
- Claude Code **Stop** hook — append a compact usage snapshot per turn to `.ccer/usage-events.jsonl` for faster reads (see §6.8)

### 3.3 How Claude Code logs behave (Mac)

Understanding this is what makes “last commit only” scoping work.

#### Session = one JSONL file

Each time Claude Code starts a **new session**, it creates:

```
~/.claude/projects/<encoded-repo>/<session-uuid>.jsonl
```

**One session ID → one file.** The filename is the session UUID. Events append to that file for the life of the session. When you quit Claude (`/exit`, close terminal, close IDE panel), the file stops growing — it is not deleted.

Verified on a real repo: four sessions in one evening, each in its own file, with no session ID appearing in more than one file.

#### What gets written, and when

| Event | What happens on disk |
|---|---|
| **Open Claude in repo** | New session file created (or resume — see below) |
| **Each prompt + response** | Lines appended continuously: `user`, `assistant`, tool results |
| **Each API turn** | Multiple `assistant` lines per turn (thinking, text, tool_use) — same `requestId`, usage on each |
| **`/clear` or compaction** | Same file keeps growing; new segment markers (`mode`, `permission-mode`, `last-prompt`) appear — not a new file |
| **Switch model (`/model`)** | No special event line; next `assistant` lines carry the new `message.model` |
| **Quit / `/exit`** | File frozen at last event; mtime stops updating |
| **Reopen later** | Usually a **new session ID** → **new JSONL file** (old files remain on disk) |
| **Resume old session** | Appends back into the **existing** JSONL file for that session ID |

Transcripts also carry `cwd`, `gitBranch`, and `entrypoint` (`cli` vs IDE) on most lines — we filter on `cwd` matching the repo under audit.

#### Parallel sessions and overlapping time

You can have **multiple session files for the same repo whose timestamps overlap**. Example from real logs:

| Session file | Time range | Notes |
|---|---|---|
| `4b6c859a…jsonl` | 02:38 – 03:49 | Long-running session, 667 lines |
| `ed8bdd36…jsonl` | 03:05 – 03:07 | Separate session opened mid-work |
| `d0e24706…jsonl` | 03:09 – 03:16 | Another fresh session for one task |
| `b5d37d60…jsonl` | 03:31 – 03:37 | Yet another |

`~/.claude/history.jsonl` records every prompt with its `sessionId` — useful for debugging, not required for v0.

**Implication for `ccer audit`:** scan **all** JSONL files in the project dir, filter by timestamp window, dedupe `requestId` globally. Never assume one session file per commit.

#### Working across commits (the common case)

Claude does **not** write a log entry when you `git commit`. Commits are invisible to the transcript — we infer the link **by time**:

```
        HEAD^                    HEAD
          │                        │
    previous commit            last commit
          │◄── usage window ──────►│
          │                        │
    ════════════════════════════════════════  one long session file
          prompts · tools · tokens keep appending
```

Typical flow:

1. Commit A — you run `ccer audit` → usage from (commit before A) → A
2. Keep working in the **same Claude session** (same JSONL file growing)
3. Commit B — `ccer audit` → usage from (A's time) → B only — **not** the whole session

Each audit slices the shared session file by commit timestamps. This is the core demo mechanic.

#### Edge cases (demo v0 behavior)

| Scenario | Behavior |
|---|---|
| **Multiple commits, one session** | Each `ccer audit` gets a non-overlapping time slice via commit timestamps |
| **Commit, then more Claude work, no new commit** | That post-commit usage is excluded from this audit (not part of HEAD yet) |
| **Claude work, no commit yet** | `ccer audit` fails gracefully: “no new commit since last audit” or audit with zero git output |
| **First commit in repo** | Usage window starts at first transcript event in repo (or session start), ends at HEAD time |
| **Commit without Claude** | Report shows git diff, zero tokens — still valid |
| **Claude in repo A, commit in repo B** | Transcript `cwd` filter excludes wrong-repo events |
| **Session spans days, audit old commit** | `--commit SHA` replays that commit's time window against frozen transcript files |

#### What we deliberately ignore for demo

- **`/usage` TUI** — not persisted; we read transcripts instead
- **Plan-level % bars** — subscription-weighted; not in JSONL
- **Other machines / claude.ai** — local transcripts only; report notes if usage may be incomplete

### 3.4 Scoping: last commit only (demo)

**Demo scope is always one commit: HEAD.** No date-range picker, no multi-commit batch.

```bash
# Git scope — the last commit only
git show HEAD --stat --numstat
git diff HEAD^..HEAD

# Usage scope — tokens that happened while this commit was being built
start = committer date of HEAD^     # parent commit (repo init if first commit)
end   = committer date of HEAD      # inclusive; not “until now”
```

Filter transcript turns where:

- `cwd` resolves to the repo under audit
- `start <= turn.timestamp <= end`
- dedupe by `requestId` across all session files in the project dir

**What this means in practice:** running `ccer audit` right after `git commit` measures the Claude cost of *that* commit, not your whole afternoon. Running it again without a new commit either no-ops or re-reports the same HEAD — we do not accumulate open-ended session usage.

CLI flags for power users (not demo path):

| Flag | Effect |
|---|---|
| `--commit SHA` | Audit a specific commit instead of HEAD (same single-commit rules) |
| `--since / --until` | Override time window (post-demo manager mode) |
| `--branch NAME` | Require matching `gitBranch` in transcripts |
| `--claude-dir PATH` | Override `~/.claude` (rare) |
| `--no-open` | Write report files only, don't open browser |

### 3.5 Model tracking

The report includes a **model breakdown** and **switch timeline** — important when engineers bounce between Sonnet and Opus mid-session.

**Sources (v0):**

1. **Assistant turns** — `message.model` on deduped `requestId` rows; aggregate tokens and cost per model
2. **Model switches** — emit a `ModelSwitch` event when `message.model` changes between consecutive deduped turns (timestamp, from → to, tokens before switch)
3. **Subagents** — parse `subagents/*.jsonl`; include `Agent` tool usage from parent transcript (`resolvedModel`, `totalTokens` in `PostToolUse` responses when present)
4. **SessionStart** — first model in a session when logged (fallback if turn data sparse)

**Report section example:**

> **Models:** Sonnet 4.6 — 98k tokens ($0.42) · Opus 4.6 — 31k tokens ($0.89)  
> **Switches:** 2 (Sonnet → Opus at 14:22 while refactoring auth; Opus → Sonnet at 15:01)

### 3.6 One-time setup (demo install)

```bash
pip install ccer          # or pip install -e .
ccer init                 # optional: install post-commit hook + print Claude dir path
```

`ccer init` writes a **post-commit hook** (opt-in) that runs `ccer audit --no-open` and drops `report.html` beside the repo or in `.ccer/reports/`. Engineer can also run manually — hook is convenience, not requirement.

Ship a **repo-local** `.claude/settings.json` snippet (optional) with an async **Stop** hook that appends turn summaries — improves reliability if Anthropic changes transcript layout, but **transcript scanning alone must work for demo**.

### 3.7 Fallbacks (when auto-read fails)

| Situation | Fallback |
|---|---|
| No `~/.claude/projects/...` for this repo | Warn + accept `--usage-file` or `--token-total` |
| Transcripts outside commit window (committed next day) | Re-run with `--commit SHA`; post-demo: `--since` override |
| First commit in repo | Window starts at first transcript event in repo |
| Demo machine without Claude | Fixture transcripts in `tests/fixtures/` |

---

## 4. Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRIMARY: CLI  `ccer audit`                   │
│  cwd = git repo  →  resolve HEAD  →  discover ~/.claude logs    │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Transcript      │ │  Git Analyzer   │ │  Session Linker │
│ Reader          │ │  (last commit)  │ │  (time + cwd)   │
│ (~/.claude)     │ │                 │ │                 │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │  Rework Detector    │
                  │  (heuristic engine) │
                  └──────────┬──────────┘
                             ▼
                  ┌─────────────────────┐
                  │  Report Generator   │
                  │  (Jinja → MD/HTML)  │
                  └─────────────────────┘

Secondary: FastAPI form at /  (batch reports, manager view, file upload fallback)
```

### Tech stack (demo)

| Layer | Choice | Why |
|---|---|---|
| Runtime | **Python 3.11+** | Rich git/subprocess ecosystem, fast to prototype |
| CLI | **`ccer audit`** (Typer/Click) | Demo-first; zero UI friction |
| API / form | **FastAPI** (secondary) | Batch reports, manager dashboard later |
| Templates | **Jinja2** | Report rendering |
| Git | **`git` CLI + GitPython** | Local repos; `gh` for PR metadata when remote |
| Usage parsing | **Pydantic + JSONL stream** | Claude Code transcript schema |
| Report output | **Markdown + HTML** | `open report.html` on Mac |
| Optional AI summaries | **Anthropic API** | Diff summaries in v0.1, not blocking demo |

**Why not Node?** Git and transcript parsing are simpler in Python for a CLI-first demo. A React UI can wrap the same API later.

---

## 5. Project Structure

```
claude-code-efficiency-report/
├── PROPOSAL.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── src/
│   └── ccer/
│       ├── __init__.py
│       ├── cli.py             # `ccer audit`, `ccer init`
│       ├── main.py            # FastAPI app (secondary)
│       ├── discovery/
│       │   └── claude_home.py # Resolve ~/.claude project dir from repo path
│       ├── models/
│       │   ├── input.py       # AuditRequest, ReportRequest
│       │   ├── usage.py       # UsageSummary, Session, ModelSwitch, ModelBreakdown
│       │   ├── git.py         # Commit, FileChange, PRInfo
│       │   └── report.py      # EfficiencyReport, ReworkFlag
│       ├── parsers/
│       │   └── transcripts.py # Read Claude Code JSONL transcripts
│       ├── analyzers/
│       │   ├── git.py
│       │   ├── rework.py
│       │   └── efficiency.py
│       ├── linker/
│       │   └── sessions.py
│       └── reports/
│           ├── generator.py
│           └── templates/
│               └── report.html.j2
├── hooks/
│   └── ccer-stop.sh           # Optional Stop hook → .ccer/usage-events.jsonl
├── tests/
│   ├── fixtures/
│   │   ├── sample_transcript.jsonl
│   │   └── sample_repo/
│   └── test_*.py
└── scripts/
    └── run_demo.sh
```

---

## 6. Module Design (Demo Scope)

### 6.1 Audit input (`models/input.py` + CLI)

**Default (zero args, run from repo root):**

| Field | Source | Notes |
|---|---|---|
| `repo_path` | `git rev-parse --show-toplevel` | Must be inside a git repo |
| `commit` | `HEAD` | Override with `--commit` |
| `engineer_name` | `git config user.name` | Override with `--author` |
| `claude_home` | `~/.claude` | Override with `--claude-dir` |
| `usage_source` | auto transcript discovery | Fallback: `--usage-file`, `--token-total` |

**Validation:**
- Repo exists and is a git repository
- Claude project dir exists OR fallback usage provided
- Commit exists and has a parseable parent (or first-commit rules apply)

```python
class AuditRequest(BaseModel):
    repo_path: Path
    commit: str = "HEAD"
    engineer_name: str | None = None
    claude_home: Path = Path.home() / ".claude"
    branch: str | None = None
    usage_file: Path | None = None      # fallback
    token_total: int | None = None      # fallback
    open_browser: bool = True
```

**Secondary `ReportRequest`** (web form / batch): date range, multi-commit, manual upload — unchanged from v0.1 but not the demo path.

---

### 6.2 Transcript reader (`parsers/transcripts.py`)

**Primary input:** Claude Code session JSONL under `~/.claude/projects/<encoded-repo>/`.

**Outputs (`UsageSummary`):**

```python
class ModelBreakdown(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    estimated_cost_usd: float
    turn_count: int

class ModelSwitch(BaseModel):
    at: datetime
    from_model: str
    to_model: str
    tokens_before_switch: int

class UsageSummary(BaseModel):
    total_tokens: int
    estimated_cost_usd: float
    session_count: int
    turn_count: int
    tokens_by_model: list[ModelBreakdown]
    model_switches: list[ModelSwitch]
    sessions: list[Session]       # id, started_at, ended_at, tokens, entrypoint
    subagent_tokens: int          # from subagents/*.jsonl
    data_source: str              # "transcripts" | "usage_file" | "token_total"
```

**Parsing strategy:**

1. **Discover project dir** — encode `repo_path` the same way Claude Code does; glob `*.jsonl` + `*/subagents/*.jsonl`
2. **Filter by time window** — `[parent_commit_time, HEAD_commit_time]` exactly (demo: no buffer)
3. **Filter by repo** — `Path(cwd).resolve()` equals or is under `repo_path`
4. **Dedupe turns** — one usage row per `requestId`; skip lines without `message.usage`
5. **Normalize tokens** — `input + output + cache_read + cache_creation`
6. **Cost estimate** — static price table keyed by model id (Sonnet/Opus/Haiku variants)
7. **Model switches** — compare deduped turn sequence per session
8. **Subagents** — same parser on nested JSONL paths

**Fallback when auto-read fails:** manual file or `token_total` with report banner *"Limited usage data — cost estimate only; no model breakdown"*.

---

### 6.3 Git diff analyzer (`analyzers/git.py`)

**Default inputs:** `repo_path`, `commit` (HEAD), optional range mode for web form.

**Data pulled via git:**

```bash
git log -1 --format=... HEAD
git log -1 --format=... HEAD^
git show HEAD --numstat
git diff HEAD^..HEAD --stat
```

**Outputs (`GitActivity`):** same as before; demo defaults to **one commit** plus its diff.

**Per-commit capture:** SHA, timestamp, subject, body, files, line stats, revert/fix tags.

**Range mode (secondary):** `--since` / `--until` for manager batch reports via web UI.

---

### 6.4 Session ↔ Git linker (`linker/sessions.py`)

For commit-scoped audit, linking is mostly **deterministic**:

1. Usage window is defined by commit timestamps (§3.3)
2. Attribute all in-window transcript events with matching `cwd` to the target commit
3. If multiple commits in window (range mode), split by committer date boundaries

**Output:** `tokens_by_commit`, `sessions_with_commits[]`, `model_switches_by_commit[]`.

---

### 6.5 Rework detector (`analyzers/rework.py`)

Same rule engine; for **single-commit audit**, rules adapt:

| Rule ID | Single-commit behavior |
|---|---|
| `FIX_KEYWORD` | Subject/body of audited commit |
| `REVERT` | Commit is a revert |
| `FILE_CHURN` | Same file touched many times *within the diff* (split patches) |
| `FOLLOW_UP_FIX` | Deferred to range mode / post-demo |
| `ADD_DELETE_SPIKE` | Large add + delete in same commit on same file |

Range mode (web form) retains full multi-commit rules from v0.1.

---

### 6.6 Efficiency assessment (`analyzers/efficiency.py`)

Same tiers and formula; reasoning template adds model context:

> "129k tokens (mostly Sonnet 4.6, 1 switch to Opus) over 3 sessions produced 840 net lines across 12 files. 1 rework flag (fix keyword in subject). Efficiency: **Medium**."

**Model-aware penalty (demo):** flag when Opus tokens > 40% of spend on low-output commits (configurable).

---

### 6.7 Report generator (`reports/generator.py`)

**Sections (manager-facing):**

1. **Executive summary** — commit subject, efficiency tier, one-line verdict
2. **Usage & cost** — total tokens, cost, sessions, **model breakdown table**, **switch timeline**
3. **Work completed** — what the commit changed (files, themes)
4. **Git evidence** — SHA, diff stat, commit message
5. **Rework analysis** — flags with evidence
6. **Code quality** (partial) — tests touched, diff size
7. **Efficiency score** — High/Med/Low + reasoning
8. **Budget recommendation**
9. **Evidence appendix** — sample diff hunks, transcript session ids

**Output:** `.ccer/reports/<sha-short>-<timestamp>.{md,html,json}` + open HTML on Mac.

---

### 6.8 Optional Claude Code hook (`hooks/ccer-stop.sh`)

Not required for demo, but recommended for dogfooding:

- Register as async **Stop** hook in `.claude/settings.json` (committed template) or via `ccer init`
- Append one JSON line per turn: `{ session_id, timestamp, model, usage, cwd, git_branch, request_id }`
- Reader merges hook file with transcript scan (hook wins on conflicts)

Avoid **SessionEnd** for transcript reads — known race where transcript file may already be deleted.

---

## 7. Claude Usage Data Sources

### Source A — Claude Code transcripts (primary, automatic)

Path pattern:

```
~/.claude/projects/-Users-<user>-<path-segments>/<uuid>.jsonl
```

Example assistant turn (abridged):

```json
{
  "type": "assistant",
  "timestamp": "2026-06-11T03:09:55.459Z",
  "cwd": "/Users/dev/my-app",
  "gitBranch": "main",
  "entrypoint": "cli",
  "sessionId": "d0e24706-5e50-4b15-9605-c90d368f49be",
  "requestId": "req_011CbvjmbVDpugyvjFziypN6",
  "message": {
    "model": "claude-sonnet-4-6",
    "usage": {
      "input_tokens": 3,
      "output_tokens": 192,
      "cache_read_input_tokens": 12034,
      "cache_creation_input_tokens": 9639
    }
  }
}
```

### Source B — Hook snapshot file (optional accelerator)

`.ccer/usage-events.jsonl` in repo, appended by Stop hook.

### Source C — Manual override (fallback)

Uploaded JSON/CSV or `{ "token_total": 250000 }` via web form / CLI flags.

Parser uses a **schema registry** — add new transcript shapes without rewriting core logic.

---

## 8. End-to-End Data Flow

**Primary (demo):**

```
1. ccer audit                          # from repo root, after commit
2. discovery.claude_project_dir()      # ~/.claude/projects/<encoded-path>
3. git_analyzer.commit_window(HEAD)    # parent..HEAD times + diff
4. transcripts.read(window, repo)      # → UsageSummary + model switches
5. session_linker.link(usage, git)     # → LinkedActivity
6. rework_detector.detect(git)         # → list[ReworkFlag]
7. efficiency.score(...)               # → EfficiencyResult
8. report_generator.render(...)        # → .ccer/reports/ + open HTML
```

**Secondary (web form):**

```
POST /api/report  { engineer, repo, dates, optional usage_file }
→ same pipeline with ReportRequest + date range instead of AuditRequest
```

**Target latency (demo):** < 5s for last-commit audit on a typical MacBook repo.

---

## 9. UI (Demo)

**Primary:** Terminal — `ccer audit` prints summary + opens `report.html`.

**Secondary:** Single-page form at `/` for batch/manager use:

- Date range, multi-commit, engineer override
- Usage file upload fallback
- Same report templates as CLI

No auth for demo.

---

## 10. Implementation Plan → July 27

| Week | Milestone |
|---|---|
| **Jun 20–22** | Scaffold, `ccer audit` CLI, Claude home discovery, transcript parser + fixtures |
| **Jun 23–26** | Git analyzer (commit window, diff, numstat) |
| **Jun 27–30** | Model breakdown + switch detection, rework detector |
| **Jul 1–5** | Efficiency scoring + report templates (model section) |
| **Jul 6–12** | `ccer init` hook, E2E dogfood on real Mac + Claude Code sessions |
| **Jul 13–20** | Edge cases (first commit, missing transcripts), web form fallback |
| **Jul 21–27** | YC demo script, 3 live commit audits, backup video |

**Demo script (3 min):**

1. Show Claude Code session in terminal (already happened — transcripts on disk)
2. `git commit` → `ccer audit` → report opens instantly
3. Scroll: model breakdown, switch timeline, diff, rework flags, efficiency
4. Close with budget recommendation

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Claude transcript schema changes | Schema registry + optional Stop hook snapshot |
| Encoded project path mismatch | Discovery self-test in `ccer doctor`; document path encoding |
| No transcripts for commit window | Report git-only + warn; fallback upload / token total |
| Duplicate usage from JSONL lines | Dedupe by `requestId` |
| SessionEnd transcript race | Read transcripts directly; hook uses Stop not SessionEnd |
| Large transcript files | Stream JSONL; filter by timestamp before full parse |
| False-positive rework flags | Show evidence; manager judges |
| IDE vs CLI sessions | Same `~/.claude`; filter by `cwd` |

---

## 12. Post-Demo Roadmap

1. **Anthropic Admin / Code Analytics API** — team rollups without local machine access
2. **GitHub App** — PR comment with efficiency summary on merge
3. **Interactive drilldown UI** — React dashboard, diff viewer
4. **LLM diff summaries** — Anthropic API for architecture narrative
5. **Team benchmarks** — tokens-per-merged-PR across engineers
6. **Policy engine** — org rules (e.g. Opus requires justification)
7. **Claude Code plugin** — `/audit` slash command → runs `ccer audit` in cwd

---

## 13. Success Criteria for Demo

- [ ] Engineer commits and runs `ccer audit` with **no manual usage export**
- [ ] Report uses **real git diff** on HEAD (not mocked)
- [ ] Token cost + **per-model breakdown** + **switch count** shown
- [ ] At least 5 rework rules fire correctly on seeded fixture repo
- [ ] Efficiency tier + budget recommendation with cited evidence
- [ ] Report is presentable to a non-technical manager in < 10 seconds after command

---

## 14. Open Questions

1. **Project path encoding** — verify encoding algorithm against Claude Code source or empirical tests on 3 repo paths.
2. **First-commit window** — start at first transcript event vs. unbounded lookback?
3. **Pricing table** — public Anthropic list prices vs plan-weighted estimates (Claude Max ≠ API list).
4. **Subagent cost attribution** — roll into parent commit or separate line item?
5. **Multi-repo sessions** — v0 attributes by `cwd`; sessions spanning repos are called out in report, not split.

---

*Proposal v0.2 — June 20, 2026*
