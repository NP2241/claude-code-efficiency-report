from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ModelBreakdown(BaseModel):
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    estimated_cost_usd: float = 0.0
    turn_count: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )


class ModelSwitch(BaseModel):
    at: datetime
    from_model: str
    to_model: str
    tokens_before_switch: int = 0


class SessionSummary(BaseModel):
    session_id: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    tokens: int = 0
    entrypoint: str | None = None


class UsageSummary(BaseModel):
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    session_count: int = 0
    turn_count: int = 0
    tokens_by_model: list[ModelBreakdown] = Field(default_factory=list)
    model_switches: list[ModelSwitch] = Field(default_factory=list)
    sessions: list[SessionSummary] = Field(default_factory=list)
    subagent_tokens: int = 0
    data_source: str = "transcripts"
    warnings: list[str] = Field(default_factory=list)
