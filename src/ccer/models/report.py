from __future__ import annotations

from pydantic import BaseModel, Field

from ccer.models.git import GitActivity
from ccer.models.usage import UsageSummary


class ReworkFlag(BaseModel):
    rule_id: str
    severity: str
    message: str
    evidence: str


class EfficiencyResult(BaseModel):
    tier: str  # High | Medium | Low
    reasoning: str
    tokens_per_net_line: float | None = None
    opus_overspend_warning: bool = False


class EfficiencyReport(BaseModel):
    executive_summary: str
    verdict: str
    usage: UsageSummary
    git: GitActivity
    rework_flags: list[ReworkFlag] = Field(default_factory=list)
    efficiency: EfficiencyResult
    budget_recommendation: str
    work_completed: str
    code_quality_notes: str = ""
    session_ids: list[str] = Field(default_factory=list)
