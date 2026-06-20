"""Efficiency tier scoring."""

from __future__ import annotations

from ccer.models.git import GitActivity
from ccer.models.report import EfficiencyResult, ReworkFlag
from ccer.models.usage import UsageSummary


def _dominant_model(usage: UsageSummary) -> str:
    if not usage.tokens_by_model:
        return "unknown"
    return usage.tokens_by_model[0].model


def _opus_share(usage: UsageSummary) -> float:
    if usage.total_tokens == 0:
        return 0.0
    opus = sum(
        m.total_tokens for m in usage.tokens_by_model if "opus" in m.model.lower()
    )
    return opus / usage.total_tokens


def score_efficiency(
    usage: UsageSummary,
    git: GitActivity,
    rework_flags: list[ReworkFlag],
) -> EfficiencyResult:
    tokens = usage.total_tokens
    net = max(abs(git.net_lines), 1)
    tpl = tokens / net if git.net_lines != 0 else float(tokens)
    rework_ids = {f.rule_id for f in rework_flags}
    opus_share = _opus_share(usage)
    low_output = abs(git.net_lines) < 15 and git.total_insertions + git.total_deletions < 30
    opus_overspend = opus_share > 0.4 and low_output and tokens > 5000

    dominant = _dominant_model(usage)
    switch_note = ""
    if usage.model_switches:
        sw = usage.model_switches[0]
        switch_note = f", 1 switch ({sw.from_model} → {sw.to_model})"

    if tokens == 0:
        tier = "High"
    elif "REVERT" in rework_ids or (tokens > 80000 and abs(git.net_lines) < 50):
        tier = "Low"
    elif "FIX_KEYWORD" in rework_ids or tokens > 50000 or opus_overspend:
        tier = "Medium"
    elif tokens < 20000 and abs(git.net_lines) >= 20:
        tier = "High"
    else:
        tier = "Medium"

    rework_note = ""
    if rework_flags:
        rework_note = f" {len(rework_flags)} rework flag(s) ({', '.join(sorted(rework_ids))})."

    reasoning = (
        f"{tokens:,} tokens (mostly {dominant}{switch_note}) over "
        f"{usage.session_count} session(s) produced {git.net_lines} net lines across "
        f"{len(git.files)} file(s).{rework_note} Efficiency: **{tier}**."
    )
    if opus_overspend:
        reasoning += " Opus accounted for >40% of spend on a low-output commit."

    return EfficiencyResult(
        tier=tier,
        reasoning=reasoning,
        tokens_per_net_line=round(tpl, 1) if git.net_lines else None,
        opus_overspend_warning=opus_overspend,
    )


def budget_recommendation(tier: str, usage: UsageSummary, git: GitActivity) -> str:
    cost = usage.estimated_cost_usd
    if tier == "High":
        return (
            f"Continue current workflow — ${cost:.2f} for this commit is reasonable "
            f"for {git.net_lines} net lines."
        )
    if tier == "Low":
        return (
            f"Review Claude usage on rework commits — ${cost:.2f} spent with "
            f"limited durable output ({git.net_lines} net lines)."
        )
    return (
        f"Monitor token spend on similar tasks — ${cost:.2f} this commit; "
        "consider smaller prompts or Sonnet for routine edits."
    )
