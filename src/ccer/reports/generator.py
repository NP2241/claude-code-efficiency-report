"""Build manager-facing efficiency reports (Markdown only)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ccer.analyzers.efficiency import budget_recommendation, score_efficiency
from ccer.analyzers.rework import detect_rework
from ccer.models.git import GitActivity
from ccer.models.report import EfficiencyReport
from ccer.models.usage import UsageSummary
from ccer.models.scenario import ScenarioTrace
from ccer.paths import reports_dir_for
from ccer.scenario.insights import build_scenario_insights


def _themes(git: GitActivity) -> str:
    paths = [f.path for f in git.files[:8]]
    if not paths:
        return "No file changes in this commit."
    return ", ".join(paths)


def build_report(usage: UsageSummary, git: GitActivity) -> EfficiencyReport:
    rework = detect_rework(git)
    efficiency = score_efficiency(usage, git, rework)
    verdict = (
        f"{efficiency.tier} efficiency — "
        f"${usage.estimated_cost_usd:.2f} · {usage.total_tokens:,} tokens · "
        f"{git.net_lines} net lines"
    )
    summary = f"**{git.commit.subject}** — {verdict}"

    quality = []
    if git.tests_touched:
        quality.append(f"Tests touched: {', '.join(git.tests_touched[:5])}")
    quality.append(
        f"Diff size: +{git.total_insertions}/-{git.total_deletions} ({len(git.files)} files)"
    )

    return EfficiencyReport(
        executive_summary=summary,
        verdict=verdict,
        usage=usage,
        git=git,
        rework_flags=rework,
        efficiency=efficiency,
        budget_recommendation=budget_recommendation(efficiency.tier, usage, git),
        work_completed=_themes(git),
        code_quality_notes=" · ".join(quality),
        session_ids=[s.session_id for s in usage.sessions],
    )


class ReportGenerator:
    def __init__(self, template_dir: Path | None = None):
        base = template_dir or Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(base)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, report: EfficiencyReport, repo_path: Path) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_dir = reports_dir_for(repo_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{report.git.commit.short_sha}-{ts}"

        ctx = {"r": report, "generated_at": datetime.now(timezone.utc).isoformat()}
        md_path = out_dir / f"{stem}.md"
        md_path.write_text(
            self.env.get_template("report.md.j2").render(**ctx),
            encoding="utf-8",
        )
        return md_path

    def render_scenario(self, trace: ScenarioTrace) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_dir = reports_dir_for(trace.repo_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / f"scenario-{trace.repo_name}-{ts}.md"
        ctx = {
            "trace": trace,
            "insights": build_scenario_insights(trace),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        md_path.write_text(
            self.env.get_template("scenario.md.j2").render(**ctx),
            encoding="utf-8",
        )
        return md_path
