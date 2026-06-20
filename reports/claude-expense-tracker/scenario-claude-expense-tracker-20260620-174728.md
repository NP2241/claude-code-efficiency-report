# CCER Dogfood Scenario Report

**Repository:** claude-expense-tracker  
**Remote:** git@github.com:NP2241/claude-expense-tracker.git  
**Generated:** 2026-06-20T17:47:28.115825+00:00

---

## What this means for the startup

This section translates the stage-by-stage breakdown below into what you'd actually **say**
to someone evaluating CCER — an eng manager, a founder, or an investor.

### The one-liner

CCER answers one question managers can't answer today: **was this Claude bill worth it?** In this run, $7.90 bought a shippable expense CLI — but $3.50 (44%) was rework you wouldn't spot in Anthropic's usage dashboard alone.

### What you'd tell an engineering manager

Your engineer shipped **14 audited commits** from a real Claude Code session. **$1.55** went to building features and tests; **$3.50** went to fixing mistakes, a reverted migration, and follow-up bug fixes. CCER ties each dollar to a git diff and flags 5 fix commits, 1 revert(s), and churn spikes — so you can coach on patterns, not argue about vibes. Efficiency breakdown: 2 High, 4 Medium, 7 Low.

**Actionable takeaways:**
- Cap Opus for small diffs — stage 3/11 patterns show expensive models on low-output commits.
- Flag reverts in standup — a revert means prior AI spend didn't stick; review before next sprint.
- Treat consecutive `fix:` commits as a smell — pair on the next similar feature before shipping.
- Run `ccer audit` after every commit (or via post-commit hook) so spend is attributed while context is fresh.

### What you'd tell an investor or early customer

**Wedge:** post-commit audit — zero workflow change, reads data Claude Code already writes locally. **Proof:** this dogfood run auto-ingested transcripts, correlated 8,059,111 tokens to 14 commits, and surfaced 8 rework signals without manual export. **Insight competitors miss:** usage dashboards show *how much*; CCER shows *what it bought* (net lines, test coverage, rework) and *what to do* (budget tier, model mix). **Expand:** team rollups, CI bot, Slack digest, Anthropic Admin API — same engine, broader surface.

### Key findings from this run
- Built a working CLI app for **$1.55** (1,095,064 tokens) across stages 1–4 — that's the "worth it" baseline.
- **$3.50** (44% of spend) went to rework: fix commits, a large refactor, and a revert — spend managers can't see in `/usage` alone.
- The SQLite migration + revert arc (stages 6–7) cost **$1.13** with **zero net code shipped** after the revert — classic invisible waste.
- **5 fix commits** triggered FIX_KEYWORD — CCER surfaces follow-up work that looks like progress in git but signals thrash in efficiency scoring.
- The deliberate bug arc (stages 12–14) added **$3.79** to fully ship one feature — a story eng leads can use for quality vs. velocity tradeoffs.
- All of this came from **1 Claude session** — CCER slices one long session into per-commit spend, not one lump-sum invoice.
- Stages 0, 7 show **0 tokens** — CCER distinguishes AI-assisted commits from manual/script-only work.
- Stage(s) 11 had no matching commit — gaps in attribution are visible, not hidden.

### Where the money went

| Category | Est. cost | Tokens | Share of spend |
|----------|-----------|--------|----------------|
| Net new feature work (stages 1–4) | $1.55 | 1,095,064 | 20% |
| Rework & follow-ups (stages 5–7, 13–14) | $3.50 | 3,857,115 | 44% |
| Other / ops / bug ship (stages 8–12, etc.) | $2.85 | 3,106,932 | 36% |
| **Total (unique commits)** | **$7.90** | **8,059,111** | **100%** |

**Efficiency tiers across commits:** 2 High · 4 Medium · 7 Low

> **The pitch in plain terms:** Anthropic tells you how many tokens you burned. Git tells you what
> changed. CCER connects the two and tells you whether the burn was productive, rework, or waste —
> automatically, after every commit, with evidence a non-technical manager can read in under 10 seconds.

---

## Scenario rollup

| Metric | Value |
|--------|-------|
| Stages defined | 15 |
| Commits audited | 14 |
| Total tokens (unique commits, all windows) | 8,059,111 |
| Total estimated cost | $7.9002 |
| Build spend (stages 1–4) | $1.55 |
| Rework spend (stages 5–7, 13–14) | $3.50 (44%) |
| Claude sessions | 1 |
| Rework flags fired | FIX_KEYWORD (5), ADD_DELETE_SPIKE (2), REVERT (1) |

**What we tested:** automatic transcript ingestion, per-commit token↔diff correlation, model
breakdown and switches, rework heuristics (fix/revert/churn), Opus overspend penalty, time-slicing
across one long session, zero-token commits, a three-commit bug arc, and historical `--commit` replay.

**Session IDs:** 4934545d-aa6b-4e2c-890d-91f657e12a5b

---

## Stage timeline

| Stage | Title | Commit | Tokens | Cost | Efficiency | Rework |
|-------|-------|--------|--------|------|------------|--------|
| 0 | Git-only baseline | chore: add gitignore | 0 | $0.0000 | High | — |
| 1 | Scaffold expense-cli | feat: add expense-cli Python CLI expense tracker | 77,224 | $0.1454 | Medium | — |
| 2 | Pytest coverage | test: add pytest suite for expense-cli (20 tests… | 204,207 | $0.3343 | Medium | — |
| 3 | Model switch (Opus refactor) | refactor: split expense_cli.py into package with… | 230,113 | $0.4922 | Low | — |
| 4 | CSV import/export | feat: add export-csv and import-csv subcommands | 583,520 | $0.5771 | Medium | — |
| 5 | FIX_KEYWORD rework | fix: strip whitespace and handle corrupt JSON in… | 399,102 | $0.4609 | Low | FIX_KEYWORD |
| 6 | SQLite migration (churn) | refactor: replace JSON storage with SQLite backe… | 1,144,115 | $1.1344 | Low | ADD_DELETE_SPIKE |
| 7 | Revert wasted work | Revert "refactor: replace JSON storage with SQLi… | 0 | $0.0000 | High | REVERT, ADD_DELETE_SPIKE |
| 8 | Time slicing | feat: add --version flag; fix broken import in t… | 1,083,706 | $0.8749 | Low | FIX_KEYWORD |
| 9 | Commit without Claude | docs: trailing newline in readme | 256,176 | $0.0941 | Low | — |
| 10 | Historical replay | fix: strip whitespace and handle corrupt JSON in… | 399,102 | $0.4609 | Low | FIX_KEYWORD |
| 11 | Opus overspend penalty | — | — | — | — | — |
| 12 | Ship the bug | feat: add --category filter to list; leave empty… | 1,767,050 | $1.8788 | Low | — |
| 13 | Fix 1 of 2 | fix: exclude empty-category rows from filtered l… | 1,048,869 | $0.8755 | Low | FIX_KEYWORD |
| 14 | Fix 2 of 2 | feat: add --category filter to summary; fix summ… | 1,265,029 | $1.0326 | Medium | FIX_KEYWORD |

---

## Full trace (stage by stage)





### Stage 0 — Git-only baseline

**Goal:** Zero-token / git-only audit  
**Expected:** 0 tokens; git diff present; efficiency High  
**Scenario:** Script adds `.gitignore` with no Claude invocation.  
**Claude used:** no (script-only)


**Matched commit:** `7ce35f38` — chore: add gitignore




**Verdict:** High efficiency — $0.00 · 0 tokens · 2 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 0 | $0.0000 | 0 | 0 | **High** |






**Rework:** none


**Files:** .ccer/dogfood-state, .gitignore




<details>
<summary>Diff stat</summary>

```
.ccer/dogfood-state | 1 +
 .gitignore          | 1 +
 2 files changed, 2 insertions(+)
```

</details>


---



### Stage 1 — Scaffold expense-cli

**Goal:** Baseline usage + diff correlation  
**Expected:** Non-zero tokens; diff shows new files  
**Scenario:** Claude builds the initial Python CLI from scratch.  
**Claude used:** yes


**Matched commit:** `5759e9cd` — feat: add expense-cli Python CLI expense tracker




**Verdict:** Medium efficiency — $0.15 · 77,224 tokens · 257 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 77,224 | $0.1454 | 13 | 1 | **Medium** |


**Models:** claude-sonnet-4-6 (77,224 tok)





**Rework:** none


**Files:** .gitignore, expense-cli/README.md, expense-cli/expense_cli.py, expense-cli/requirements.txt




<details>
<summary>Diff stat</summary>

```
.gitignore                   |   3 +-
 expense-cli/README.md        |  86 ++++++++++++++++++++++
 expense-cli/expense_cli.py   | 168 +++++++++++++++++++++++++++++++++++++++++++
 expense-cli/requirements.txt |   2 +
 4 files changed, 258 insertions(+), 1 deletion(-)
```

</details>


---



### Stage 2 — Pytest coverage

**Goal:** Tests touched, efficiency baseline  
**Expected:** Lower tokens than stage 1; tests mentioned  
**Scenario:** Claude adds pytest tests for add/list/summary.  
**Claude used:** yes


**Matched commit:** `2b39b6cd` — test: add pytest suite for expense-cli (20 tests)




**Verdict:** Medium efficiency — $0.33 · 204,207 tokens · 226 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 204,207 | $0.3343 | 9 | 1 | **Medium** |


**Models:** claude-sonnet-4-6 (204,207 tok)





**Rework:** none


**Files:** .gitignore, expense-cli/conftest.py, expense-cli/requirements.txt, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
.gitignore                            |   9 ++
 expense-cli/conftest.py               |   2 +
 expense-cli/requirements.txt          |   7 +-
 expense-cli/tests/test_expense_cli.py | 212 ++++++++++++++++++++++++++++++++++
 4 files changed, 228 insertions(+), 2 deletions(-)
```

</details>


---



### Stage 3 — Model switch (Opus refactor)

**Goal:** Model breakdown + switch timeline  
**Expected:** 2+ models; switch timeline entry  
**Scenario:** Opus refactors single module into a package (model switch test).  
**Claude used:** yes


**Matched commit:** `803b8fe2` — refactor: split expense_cli.py into package with cli, storage, models




**Verdict:** Low efficiency — $0.49 · 230,113 tokens · 29 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 230,113 | $0.4922 | 8 | 1 | **Low** |


**Models:** claude-opus-4-6 (230,113 tok)





**Rework:** none


**Files:** .ccer/claude-last.json, .ccer/dogfood-state, expense-cli/expense_cli/__init__.py, expense-cli/expense_cli/__main__.py, expense-cli/{expense_cli.py => expense_cli/cli.py}, expense-cli/expense_cli/models.py, expense-cli/expense_cli/storage.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
.ccer/claude-last.json                             |  1 -
 .ccer/dogfood-state                                |  2 +-
 expense-cli/expense_cli/__init__.py                |  1 +
 expense-cli/expense_cli/__main__.py                |  5 ++
 expense-cli/{expense_cli.py => expense_cli/cli.py} | 82 +++++++++-------------
 expense-cli/expense_cli/models.py                  | 22 ++++++
 expense-cli/expense_cli/storage.py                 | 20 ++++++
 expense-cli/tests/test_expense_cli.py              | 48 ++++++-------
 8 files changed, 105 insertions(+), 76 deletions(-)
```

</details>


---



### Stage 4 — CSV import/export

**Goal:** High turn count / tool loops  
**Expected:** Higher turn count; tool loop evidence  
**Scenario:** Claude adds CSV commands and runs pytest in a loop.  
**Claude used:** yes


**Matched commit:** `8a38cdd1` — feat: add export-csv and import-csv subcommands




**Verdict:** Medium efficiency — $0.58 · 583,520 tokens · 264 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 583,520 | $0.5771 | 11 | 1 | **Medium** |


**Models:** claude-sonnet-4-6 (549,567 tok) · claude-opus-4-6 (33,953 tok)



**Switches:** claude-opus-4-6→claude-sonnet-4-6 at 17:08



**Rework:** none


**Files:** expense-cli/README.md, expense-cli/expense_cli/cli.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
expense-cli/README.md                 |  74 +++++++++++++----
 expense-cli/expense_cli/cli.py        |  76 ++++++++++++++++++
 expense-cli/tests/test_expense_cli.py | 146 +++++++++++++++++++++++++++++++++-
 3 files changed, 280 insertions(+), 16 deletions(-)
```

</details>


---



### Stage 5 — FIX_KEYWORD rework

**Goal:** FIX_KEYWORD rework flag  
**Expected:** FIX_KEYWORD flag; Medium/Low efficiency  
**Scenario:** Claude fixes corrupt JSON handling — `fix:` commit.  
**Claude used:** yes


**Matched commit:** `4dff781b` — fix: strip whitespace and handle corrupt JSON in storage.load()




**Verdict:** Low efficiency — $0.46 · 399,102 tokens · 40 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 399,102 | $0.4609 | 6 | 1 | **Low** |


**Models:** claude-sonnet-4-6 (399,102 tok)





**Rework:** `FIX_KEYWORD`


**Files:** expense-cli/expense_cli/storage.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
expense-cli/expense_cli/storage.py    | 20 ++++++++++++++++++--
 expense-cli/tests/test_expense_cli.py | 24 ++++++++++++++++++++++++
 2 files changed, 42 insertions(+), 2 deletions(-)
```

</details>


---



### Stage 6 — SQLite migration (churn)

**Goal:** ADD_DELETE_SPIKE / file churn  
**Expected:** Churn flag on rewritten files  
**Scenario:** Claude rewrites storage for SQLite (large churn).  
**Claude used:** yes


**Matched commit:** `1854f401` — refactor: replace JSON storage with SQLite backend (expenses.db)




**Verdict:** Low efficiency — $1.13 · 1,144,115 tokens · 21 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 1,144,115 | $1.1344 | 11 | 1 | **Low** |


**Models:** claude-sonnet-4-6 (1,144,115 tok)





**Rework:** `ADD_DELETE_SPIKE`


**Files:** .gitignore, expense-cli/README.md, expense-cli/expense_cli/cli.py, expense-cli/expense_cli/models.py, expense-cli/expense_cli/storage.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
.gitignore                            |   6 +-
 expense-cli/README.md                 |  31 +++--
 expense-cli/expense_cli/cli.py        |  17 +--
 expense-cli/expense_cli/models.py     |  17 +--
 expense-cli/expense_cli/storage.py    |  85 ++++++++----
 expense-cli/tests/test_expense_cli.py | 253 +++++++++++++++++-----------------
 6 files changed, 215 insertions(+), 194 deletions(-)
```

</details>


---



### Stage 7 — Revert wasted work

**Goal:** REVERT rework flag  
**Expected:** REVERT flag; Low efficiency narrative  
**Scenario:** Script reverts SQLite migration — no Claude (wasted prior spend).  
**Claude used:** no (script-only)


**Matched commit:** `e87307d0` — Revert "refactor: replace JSON storage with SQLite backend (expenses.db)"




**Verdict:** High efficiency — $0.00 · 0 tokens · -21 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 0 | $0.0000 | 0 | 0 | **High** |






**Rework:** `REVERT`, `ADD_DELETE_SPIKE`


**Files:** .gitignore, expense-cli/README.md, expense-cli/expense_cli/cli.py, expense-cli/expense_cli/models.py, expense-cli/expense_cli/storage.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
.gitignore                            |   6 +-
 expense-cli/README.md                 |  31 ++---
 expense-cli/expense_cli/cli.py        |  17 ++-
 expense-cli/expense_cli/models.py     |  17 ++-
 expense-cli/expense_cli/storage.py    |  85 ++++--------
 expense-cli/tests/test_expense_cli.py | 253 +++++++++++++++++-----------------
 6 files changed, 194 insertions(+), 215 deletions(-)
```

</details>


---



### Stage 8 — Time slicing

**Goal:** Time slicing in shared Claude session  
**Expected:** Small token slice vs early stages  
**Scenario:** Tiny change in the same Claude session — proves commit time windows.  
**Claude used:** yes


**Matched commit:** `7b6dd547` — feat: add --version flag; fix broken import in tests




**Verdict:** Low efficiency — $0.87 · 1,083,706 tokens · 16 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 1,083,706 | $0.8749 | 9 | 1 | **Low** |


**Models:** claude-sonnet-4-6 (1,083,706 tok)





**Rework:** `FIX_KEYWORD`


**Files:** expense-cli/expense_cli/cli.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
expense-cli/expense_cli/cli.py        |  3 +++
 expense-cli/tests/test_expense_cli.py | 13 +++++++++++++
 2 files changed, 16 insertions(+)
```

</details>


---



### Stage 9 — Commit without Claude

**Goal:** Commit without Claude usage  
**Expected:** ~0 tokens; efficiency High  
**Scenario:** Script appends README newline — simulates manual docs edit.  
**Claude used:** no (script-only)


**Matched commit:** `db24b649` — docs: trailing newline in readme




**Verdict:** Low efficiency — $0.09 · 256,176 tokens · 1 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 256,176 | $0.0941 | 2 | 1 | **Low** |


**Models:** claude-sonnet-4-6 (256,176 tok)





**Rework:** none


**Files:** README.md




<details>
<summary>Diff stat</summary>

```
README.md | 1 +
 1 file changed, 1 insertion(+)
```

</details>


---



### Stage 10 — Historical replay

**Goal:** Historical --commit replay  
**Expected:** Same report as original stage 5 audit  
**Scenario:** Re-audit of stage 5 fix commit — no new commit (validation only).  
**Claude used:** no (script-only)


**Matched commit:** `4dff781b` — fix: strip whitespace and handle corrupt JSON in storage.load()




**Verdict:** Low efficiency — $0.46 · 399,102 tokens · 40 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 399,102 | $0.4609 | 6 | 1 | **Low** |


**Models:** claude-sonnet-4-6 (399,102 tok)





**Rework:** `FIX_KEYWORD`


**Files:** expense-cli/expense_cli/storage.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
expense-cli/expense_cli/storage.py    | 20 ++++++++++++++++++--
 expense-cli/tests/test_expense_cli.py | 24 ++++++++++++++++++++++++
 2 files changed, 42 insertions(+), 2 deletions(-)
```

</details>


---



### Stage 11 — Opus overspend penalty

**Goal:** Opus overspend on low-output commit  
**Expected:** Opus >40% on tiny diff; efficiency penalty  
**Scenario:** Opus fixes a one-word README typo (overspend test). Skipped if no dedicated typo commit landed.  
**Claude used:** yes


**Status:** No matching commit in git history for this stage.




---



### Stage 12 — Ship the bug

**Goal:** Introduce deliberate category-filter bug  
**Expected:** Feature commit with hidden bug  
**Scenario:** Claude ships `--category` on list with empty-category bug left in.  
**Claude used:** yes


**Matched commit:** `c18582d1` — feat: add --category filter to list; leave empty-category bug in place




**Verdict:** Low efficiency — $1.88 · 1,767,050 tokens · 16 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 1,767,050 | $1.8788 | 17 | 1 | **Low** |


**Models:** claude-opus-4-6 (1,050,834 tok) · claude-sonnet-4-6 (716,216 tok)



**Switches:** claude-opus-4-6→claude-sonnet-4-6 at 17:25



**Rework:** none


**Files:** expense-cli/expense_cli/cli.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
expense-cli/expense_cli/cli.py        |  7 +++++--
 expense-cli/tests/test_expense_cli.py | 13 +++++++++++++
 2 files changed, 18 insertions(+), 2 deletions(-)
```

</details>


---



### Stage 13 — Fix 1 of 2

**Goal:** Follow-up fix (partial)  
**Expected:** FIX_KEYWORD; list fixed, summary still broken  
**Scenario:** First fix commit — list filter patched, summary bug remains.  
**Claude used:** yes


**Matched commit:** `0d44f141` — fix: exclude empty-category rows from filtered list output




**Verdict:** Low efficiency — $0.88 · 1,048,869 tokens · 7 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 1,048,869 | $0.8755 | 7 | 1 | **Low** |


**Models:** claude-sonnet-4-6 (1,048,869 tok)





**Rework:** `FIX_KEYWORD`


**Files:** expense-cli/expense_cli/cli.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
expense-cli/expense_cli/cli.py        |  7 ++-----
 expense-cli/tests/test_expense_cli.py | 10 ++++++++++
 2 files changed, 12 insertions(+), 5 deletions(-)
```

</details>


---



### Stage 14 — Fix 2 of 2

**Goal:** Follow-up fix (complete)  
**Expected:** FIX_KEYWORD; bug fully resolved  
**Scenario:** Second fix commit — category filter works end-to-end.  
**Claude used:** yes


**Matched commit:** `7e713c46` — feat: add --category filter to summary; fix summary double-count bug




**Verdict:** Medium efficiency — $1.03 · 1,265,029 tokens · 50 net lines

| Tokens | Cost | Turns | Sessions | Efficiency |
|--------|------|-------|----------|------------|
| 1,265,029 | $1.0326 | 8 | 1 | **Medium** |


**Models:** claude-sonnet-4-6 (1,265,029 tok)





**Rework:** `FIX_KEYWORD`


**Files:** expense-cli/expense_cli/cli.py, expense-cli/tests/test_expense_cli.py




<details>
<summary>Diff stat</summary>

```
expense-cli/expense_cli/cli.py        | 22 ++++++++++++++++++++--
 expense-cli/tests/test_expense_cli.py | 32 ++++++++++++++++++++++++++++++++
 2 files changed, 52 insertions(+), 2 deletions(-)
```

</details>


---



## Demo narrative (3-minute walkthrough)

1. **Setup** — Engineer opens Claude Code in `claude-expense-tracker`, runs dogfood stages via `dogfood.sh`.
2. **Productive work** — Stages 1–4 build and test the expense CLI; tokens correlate with real diffs.
3. **Model switch** — Stage 3 Opus refactor shows per-model breakdown in the report.
4. **Rework story** — Stage 5 fix, Stage 6 churn, Stage 7 revert = cautionary efficiency tale.
5. **Time slicing** — Stage 8 tiny commit proves audits scope to commit windows, not whole sessions.
6. **Bug arc** — Stages 12→13→14: ship bug, two fix commits, FIX_KEYWORD flags each time.
7. **Manager view** — Lead with **What this means for the startup** above; drill into stages on request.

## Files produced

Per-commit audits: `reports/<repo>/<sha>-<timestamp>.md` (in this CCER repo)  
This scenario trace: `reports/<repo>/scenario-<repo>-<timestamp>.md`

---

*Generated by `ccer scenario` — CCER dogfood playbook*