"""Resolve CCER project paths for report output."""

from __future__ import annotations

from pathlib import Path


def find_ccer_project_root() -> Path:
    """Locate the claude-code-efficiency-report project root (contains pyproject.toml)."""
    start = Path(__file__).resolve().parent
    for path in [start, *start.parents]:
        if (path / "pyproject.toml").is_file() and (path / "src" / "ccer").is_dir():
            return path
    return start.parents[1]


def reports_dir_for(audited_repo: Path, ccer_root: Path | None = None) -> Path:
    """Reports for an audited repo live under <ccer-root>/reports/<repo-name>/."""
    root = ccer_root or find_ccer_project_root()
    return root / "reports" / audited_repo.resolve().name
