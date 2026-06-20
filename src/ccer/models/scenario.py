"""Scenario trace models for full dogfood reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ccer.models.report import EfficiencyReport
from ccer.scenario.stages import ScenarioStage


@dataclass
class CommitRef:
    sha: str
    subject: str


@dataclass
class StageTrace:
    stage: ScenarioStage
    commit: CommitRef | None = None
    report: EfficiencyReport | None = None
    skipped_reason: str = ""


@dataclass
class ScenarioTrace:
    repo_path: Path
    repo_name: str
    github_remote: str
    stages: list[StageTrace] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        seen: set[str] = set()
        total = 0
        for st in self.stages:
            if not st.report or not st.commit:
                continue
            if st.commit.sha in seen:
                continue
            seen.add(st.commit.sha)
            total += st.report.usage.total_tokens
        return total

    @property
    def total_cost_usd(self) -> float:
        seen: set[str] = set()
        total = 0.0
        for st in self.stages:
            if not st.report or not st.commit:
                continue
            if st.commit.sha in seen:
                continue
            seen.add(st.commit.sha)
            total += st.report.usage.estimated_cost_usd
        return total

    @property
    def audited_commits(self) -> int:
        return sum(1 for s in self.stages if s.report)

    @property
    def rework_flag_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for st in self.stages:
            if not st.report:
                continue
            for flag in st.report.rework_flags:
                counts[flag.rule_id] = counts.get(flag.rule_id, 0) + 1
        return counts
