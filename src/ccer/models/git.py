from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    path: str
    insertions: int = 0
    deletions: int = 0


class CommitInfo(BaseModel):
    sha: str
    short_sha: str
    subject: str
    body: str = ""
    author_name: str = ""
    committed_at: datetime
    parent_sha: str | None = None
    is_merge: bool = False
    is_revert: bool = False


class GitActivity(BaseModel):
    commit: CommitInfo
    parent: CommitInfo | None = None
    window_start: datetime
    window_end: datetime
    files: list[FileChange] = Field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0
    net_lines: int = 0
    diff_stat: str = ""
    diff_patch: str = ""
    tests_touched: list[str] = Field(default_factory=list)
