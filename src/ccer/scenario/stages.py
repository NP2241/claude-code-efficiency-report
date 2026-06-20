"""Dogfood test stage definitions — mirrors scripts/dogfood_stages.sh and test.md."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScenarioStage:
    stage_id: int
    title: str
    goal: str
    expected: str
    commit_patterns: list[str] = field(default_factory=list)
    uses_claude: bool = True
    scenario_note: str = ""


DOGFOOD_SCENARIO: list[ScenarioStage] = [
    ScenarioStage(
        0,
        "Git-only baseline",
        "Zero-token / git-only audit",
        "0 tokens; git diff present; efficiency High",
        ["chore: add gitignore"],
        uses_claude=False,
        scenario_note="Script adds `.gitignore` with no Claude invocation.",
    ),
    ScenarioStage(
        1,
        "Scaffold expense-cli",
        "Baseline usage + diff correlation",
        "Non-zero tokens; diff shows new files",
        [
            "feat: add expense-cli with add, list, and summary",
            "expense-cli python cli expense tracker",
            "add expense-cli",
        ],
        scenario_note="Claude builds the initial Python CLI from scratch.",
    ),
    ScenarioStage(
        2,
        "Pytest coverage",
        "Tests touched, efficiency baseline",
        "Lower tokens than stage 1; tests mentioned",
        ["pytest coverage", "pytest suite", "test: add pytest"],
        scenario_note="Claude adds pytest tests for add/list/summary.",
    ),
    ScenarioStage(
        3,
        "Model switch (Opus refactor)",
        "Model breakdown + switch timeline",
        "2+ models; switch timeline entry",
        [
            "refactor: split expense-cli into package",
            "split expense_cli.py into package",
            "split into package modules",
        ],
        scenario_note="Opus refactors single module into a package (model switch test).",
    ),
    ScenarioStage(
        4,
        "CSV import/export",
        "High turn count / tool loops",
        "Higher turn count; tool loop evidence",
        ["csv import and export", "export-csv", "import-csv", "csv import"],
        scenario_note="Claude adds CSV commands and runs pytest in a loop.",
    ),
    ScenarioStage(
        5,
        "FIX_KEYWORD rework",
        "FIX_KEYWORD rework flag",
        "FIX_KEYWORD flag; Medium/Low efficiency",
        [
            "corrupt expenses.json",
            "corrupt json",
            "strip whitespace",
            "empty lines in summary",
        ],
        scenario_note="Claude fixes corrupt JSON handling — `fix:` commit.",
    ),
    ScenarioStage(
        6,
        "SQLite migration (churn)",
        "ADD_DELETE_SPIKE / file churn",
        "Churn flag on rewritten files",
        ["replace json storage with sqlite", "sqlite backend", "migrate storage from json to sqlite"],
        scenario_note="Claude rewrites storage for SQLite (large churn).",
    ),
    ScenarioStage(
        7,
        "Revert wasted work",
        "REVERT rework flag",
        "REVERT flag; Low efficiency narrative",
        ["revert"],
        uses_claude=False,
        scenario_note="Script reverts SQLite migration — no Claude (wasted prior spend).",
    ),
    ScenarioStage(
        8,
        "Time slicing",
        "Time slicing in shared Claude session",
        "Small token slice vs early stages",
        ["--version", "version flag"],
        scenario_note="Tiny change in the same Claude session — proves commit time windows.",
    ),
    ScenarioStage(
        9,
        "Commit without Claude",
        "Commit without Claude usage",
        "~0 tokens; efficiency High",
        ["trailing newline", "docs: trailing"],
        uses_claude=False,
        scenario_note="Script appends README newline — simulates manual docs edit.",
    ),
    ScenarioStage(
        10,
        "Historical replay",
        "Historical --commit replay",
        "Same report as original stage 5 audit",
        [],
        uses_claude=False,
        scenario_note="Re-audit of stage 5 fix commit — no new commit (validation only).",
    ),
    ScenarioStage(
        11,
        "Opus overspend penalty",
        "Opus overspend on low-output commit",
        "Opus >40% on tiny diff; efficiency penalty",
        ["fix typo in readme", "typo in readme"],
        scenario_note="Opus fixes a one-word README typo (overspend test). Skipped if no dedicated typo commit landed.",
    ),
    ScenarioStage(
        12,
        "Ship the bug",
        "Introduce deliberate category-filter bug",
        "Feature commit with hidden bug",
        ["category filter to list", "leave empty-category bug", "empty-category bug in place"],
        scenario_note="Claude ships `--category` on list with empty-category bug left in.",
    ),
    ScenarioStage(
        13,
        "Fix 1 of 2",
        "Follow-up fix (partial)",
        "FIX_KEYWORD; list fixed, summary still broken",
        ["exclude empty category", "empty-category rows", "filtered list"],
        scenario_note="First fix commit — list filter patched, summary bug remains.",
    ),
    ScenarioStage(
        14,
        "Fix 2 of 2",
        "Follow-up fix (complete)",
        "FIX_KEYWORD; bug fully resolved",
        ["category filter to summary", "summary double-count", "category-filtered summary"],
        scenario_note="Second fix commit — category filter works end-to-end.",
    ),
]

# Commits to skip when auto-matching stages (metadata / noise)
SKIP_COMMIT_PATTERNS = [
    "gitignore .ccer metadata",
    "feat: migrate storage from json to sqlite",  # dogfood metadata-only duplicate
]
