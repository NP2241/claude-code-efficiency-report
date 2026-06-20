"""Turn scenario trace data into manager- and investor-facing narrative."""

from __future__ import annotations

from dataclasses import dataclass, field

from ccer.models.scenario import ScenarioTrace

# Stage groupings for spend narrative (dogfood playbook)
_BUILD_STAGES = {1, 2, 3, 4}
_REWORK_STAGES = {5, 6, 7, 13, 14}
_WASTED_STAGES = {6, 7}  # churn + revert arc
_BUG_ARC_STAGES = {12, 13, 14}


@dataclass
class SpendBucket:
    label: str
    cost_usd: float
    tokens: int
    stage_ids: list[int]
    pct_of_total: float = 0.0


@dataclass
class ScenarioInsights:
    elevator_pitch: str
    manager_brief: str
    investor_brief: str
    key_findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    spend_buckets: list[SpendBucket] = field(default_factory=list)
    efficiency_counts: dict[str, int] = field(default_factory=dict)
    rework_cost_usd: float = 0.0
    build_cost_usd: float = 0.0
    wasted_cost_usd: float = 0.0
    rework_pct: float = 0.0


def _deduped_stage_costs(trace: ScenarioTrace) -> dict[int, tuple[float, int]]:
    seen: set[str] = set()
    out: dict[int, tuple[float, int]] = {}
    for st in trace.stages:
        if not st.report or not st.commit:
            continue
        if st.commit.sha in seen:
            continue
        seen.add(st.commit.sha)
        out[st.stage.stage_id] = (
            st.report.usage.estimated_cost_usd,
            st.report.usage.total_tokens,
        )
    return out


def _sum_stages(costs: dict[int, tuple[float, int]], stage_ids: set[int]) -> tuple[float, int]:
    cost = tokens = 0
    for sid in stage_ids:
        if sid in costs:
            c, t = costs[sid]
            cost += c
            tokens += t
    return cost, tokens


def build_scenario_insights(trace: ScenarioTrace) -> ScenarioInsights:
    costs = _deduped_stage_costs(trace)
    total_cost = trace.total_cost_usd
    total_tokens = trace.total_tokens

    build_cost, build_tokens = _sum_stages(costs, _BUILD_STAGES)
    rework_cost, rework_tokens = _sum_stages(costs, _REWORK_STAGES)
    wasted_cost, wasted_tokens = _sum_stages(costs, _WASTED_STAGES)
    bug_cost, bug_tokens = _sum_stages(costs, _BUG_ARC_STAGES)

    rework_pct = (rework_cost / total_cost * 100) if total_cost > 0 else 0.0

    efficiency_counts: dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
    seen_eff: set[str] = set()
    for st in trace.stages:
        if not st.report or not st.commit or st.commit.sha in seen_eff:
            continue
        seen_eff.add(st.commit.sha)
        tier = st.report.efficiency.tier
        efficiency_counts[tier] = efficiency_counts.get(tier, 0) + 1

    rework_flags = trace.rework_flag_counts
    fix_count = rework_flags.get("FIX_KEYWORD", 0)
    revert_count = rework_flags.get("REVERT", 0)
    churn_count = rework_flags.get("ADD_DELETE_SPIKE", 0)

    low_count = efficiency_counts.get("Low", 0)
    audited = trace.audited_commits

    # --- Key findings (data-driven bullets) ---
    findings: list[str] = []

    findings.append(
        f"Built a working CLI app for **${build_cost:.2f}** ({build_tokens:,} tokens) "
        f"across stages 1–4 — that's the \"worth it\" baseline."
    )

    if rework_cost > 0:
        findings.append(
            f"**${rework_cost:.2f}** ({rework_pct:.0f}% of spend) went to rework: "
            f"fix commits, a large refactor, and a revert — spend managers can't see in `/usage` alone."
        )

    if wasted_cost > 0 and revert_count:
        findings.append(
            f"The SQLite migration + revert arc (stages 6–7) cost **${wasted_cost:.2f}** "
            f"with **zero net code shipped** after the revert — classic invisible waste."
        )

    if fix_count >= 2:
        findings.append(
            f"**{fix_count} fix commits** triggered FIX_KEYWORD — CCER surfaces follow-up work "
            f"that looks like progress in git but signals thrash in efficiency scoring."
        )

    if bug_cost > 0:
        findings.append(
            f"The deliberate bug arc (stages 12–14) added **${bug_cost:.2f}** to fully ship "
            f"one feature — a story eng leads can use for quality vs. velocity tradeoffs."
        )

    if trace.session_ids:
        n = len(trace.session_ids)
        session_label = "session" if n == 1 else "sessions"
        findings.append(
            f"All of this came from **{n} Claude {session_label}** — "
            f"CCER slices one long session into per-commit spend, not one lump-sum invoice."
        )

    zero_token_stages = [
        st.stage.stage_id
        for st in trace.stages
        if st.report and st.report.usage.total_tokens == 0 and st.commit
    ]
    if zero_token_stages:
        findings.append(
            f"Stages {', '.join(str(s) for s in zero_token_stages)} show **0 tokens** — "
            f"CCER distinguishes AI-assisted commits from manual/script-only work."
        )

    skipped = [st.stage.stage_id for st in trace.stages if not st.report and st.stage.uses_claude]
    if skipped:
        findings.append(
            f"Stage(s) {', '.join(str(s) for s in skipped)} had no matching commit — "
            f"gaps in attribution are visible, not hidden."
        )

    # --- Recommendations ---
    recommendations: list[str] = []
    if rework_pct > 15:
        recommendations.append(
            "Cap Opus for small diffs — stage 3/11 patterns show expensive models on low-output commits."
        )
    if revert_count:
        recommendations.append(
            "Flag reverts in standup — a revert means prior AI spend didn't stick; review before next sprint."
        )
    if fix_count >= 2:
        recommendations.append(
            "Treat consecutive `fix:` commits as a smell — pair on the next similar feature before shipping."
        )
    if low_count > audited // 2:
        recommendations.append(
            "More than half of commits scored Low/Medium — team may need clearer task scoping in Claude prompts."
        )
    recommendations.append(
        "Run `ccer audit` after every commit (or via post-commit hook) so spend is attributed while context is fresh."
    )

    # --- Spend buckets for table ---
    other_cost = max(0.0, total_cost - build_cost - rework_cost)
    other_tokens = max(0, total_tokens - build_tokens - rework_tokens)
    buckets = [
        SpendBucket("Net new feature work (stages 1–4)", build_cost, build_tokens, sorted(_BUILD_STAGES)),
        SpendBucket("Rework & follow-ups (stages 5–7, 13–14)", rework_cost, rework_tokens, sorted(_REWORK_STAGES)),
        SpendBucket("Other / ops / bug ship (stages 8–12, etc.)", other_cost, other_tokens, []),
    ]
    for b in buckets:
        b.pct_of_total = (b.cost_usd / total_cost * 100) if total_cost > 0 else 0.0

    # --- Narrative blocks ---
    elevator = (
        f"CCER answers one question managers can't answer today: **was this Claude bill worth it?** "
        f"In this run, ${total_cost:.2f} bought a shippable expense CLI — but "
        f"${rework_cost:.2f} ({rework_pct:.0f}%) was rework you wouldn't spot in Anthropic's usage dashboard alone."
    )

    manager = (
        f"Your engineer shipped **{audited} audited commits** from a real Claude Code session. "
        f"**${build_cost:.2f}** went to building features and tests; **${rework_cost:.2f}** went to "
        f"fixing mistakes, a reverted migration, and follow-up bug fixes. "
        f"CCER ties each dollar to a git diff and flags {fix_count} fix commits"
        f"{', ' + str(revert_count) + ' revert(s)' if revert_count else ''}"
        f"{', and churn spikes' if churn_count else ''} — "
        f"so you can coach on patterns, not argue about vibes. "
        f"Efficiency breakdown: {efficiency_counts.get('High', 0)} High, "
        f"{efficiency_counts.get('Medium', 0)} Medium, {efficiency_counts.get('Low', 0)} Low."
    )

    investor = (
        f"**Wedge:** post-commit audit — zero workflow change, reads data Claude Code already writes locally. "
        f"**Proof:** this dogfood run auto-ingested transcripts, correlated {total_tokens:,} tokens to "
        f"{audited} commits, and surfaced {sum(rework_flags.values())} rework signals without manual export. "
        f"**Insight competitors miss:** usage dashboards show *how much*; CCER shows *what it bought* "
        f"(net lines, test coverage, rework) and *what to do* (budget tier, model mix). "
        f"**Expand:** team rollups, CI bot, Slack digest, Anthropic Admin API — same engine, broader surface."
    )

    return ScenarioInsights(
        elevator_pitch=elevator,
        manager_brief=manager,
        investor_brief=investor,
        key_findings=findings,
        recommendations=recommendations,
        spend_buckets=buckets,
        efficiency_counts=efficiency_counts,
        rework_cost_usd=rework_cost,
        build_cost_usd=build_cost,
        wasted_cost_usd=wasted_cost,
        rework_pct=rework_pct,
    )
