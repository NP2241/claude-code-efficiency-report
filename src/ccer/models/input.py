from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    repo_path: Path
    commit: str = "HEAD"
    engineer_name: str | None = None
    claude_home: Path = Field(default_factory=lambda: Path.home() / ".claude")
    branch: str | None = None
    usage_file: Path | None = None
    token_total: int | None = None
