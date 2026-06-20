"""Resolve Claude Code project directories from repo paths."""

from __future__ import annotations

from pathlib import Path


def encode_repo_path(repo_path: Path) -> str:
    resolved = repo_path.resolve()
    return "-" + str(resolved).lstrip("/").replace("/", "-")


def claude_project_dir(repo_path: Path, claude_home: Path | None = None) -> Path | None:
    home = claude_home or Path.home() / ".claude"
    project_dir = home / "projects" / encode_repo_path(repo_path)
    return project_dir if project_dir.is_dir() else None
