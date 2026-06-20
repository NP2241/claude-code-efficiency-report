"""Match git history to dogfood stages and build a full scenario trace."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ccer.analyzers.git import analyze_commit
from ccer.discovery.claude_home import claude_project_dir
from ccer.models.report import EfficiencyReport
from ccer.models.scenario import CommitRef, ScenarioTrace, StageTrace
from ccer.parsers.transcripts import read_transcripts
from ccer.reports.generator import build_report
from ccer.scenario.stages import DOGFOOD_SCENARIO, SKIP_COMMIT_PATTERNS


def _git_log_commits(repo: Path) -> list[CommitRef]:
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--format=%H|%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    commits: list[CommitRef] = []
    for line in out.stdout.strip().splitlines():
        if "|" not in line:
            continue
        sha, subject = line.split("|", 1)
        subj_l = subject.lower()
        if any(skip.lower() in subj_l for skip in SKIP_COMMIT_PATTERNS):
            continue
        if subject.strip() in ("chore: init repo",):
            continue
        commits.append(CommitRef(sha=sha, subject=subject))
    return commits


def _matches(subject: str, patterns: list[str]) -> bool:
    if not patterns:
        return False
    subj = subject.lower()
    return any(p.lower() in subj for p in patterns)


def _assign_commits(commits: list[CommitRef]) -> dict[int, CommitRef]:
    used: set[str] = set()
    mapping: dict[int, CommitRef] = {}
    for stage in DOGFOOD_SCENARIO:
        if not stage.commit_patterns:
            continue
        for commit in commits:
            if commit.sha in used:
                continue
            if _matches(commit.subject, stage.commit_patterns):
                mapping[stage.stage_id] = commit
                used.add(commit.sha)
                break
    return mapping


def _audit_commit(
    repo: Path,
    sha: str,
    claude_home: Path,
) -> EfficiencyReport:
    git = analyze_commit(repo, sha)
    project_dir = claude_project_dir(repo, claude_home)
    if project_dir is None:
        usage = read_transcripts(Path("/nonexistent"), repo, git.window_start, git.window_end)
        usage.warnings.append("No Claude transcripts found for this repo.")
    else:
        usage = read_transcripts(project_dir, repo, git.window_start, git.window_end)
    return build_report(usage, git)


def build_scenario_trace(
    repo_path: Path,
    claude_home: Path | None = None,
    github_remote: str = "",
) -> ScenarioTrace:
    repo = repo_path.resolve()
    home = claude_home or Path.home() / ".claude"
    commits = _git_log_commits(repo)
    assigned = _assign_commits(commits)

    if not github_remote:
        try:
            github_remote = subprocess.run(
                ["git", "-C", str(repo), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except subprocess.CalledProcessError:
            github_remote = ""

    trace = ScenarioTrace(
        repo_path=repo,
        repo_name=repo.name,
        github_remote=github_remote,
    )
    all_sessions: set[str] = set()

    for stage in DOGFOOD_SCENARIO:
        entry = StageTrace(stage=stage)

        if stage.stage_id == 10:
            fix_commit = assigned.get(5)
            if fix_commit:
                entry.commit = fix_commit
                entry.report = _audit_commit(repo, fix_commit.sha, home)
                entry.skipped_reason = "Replay audit of stage 5 commit (no new git commit)."
            else:
                entry.skipped_reason = "Stage 5 fix commit not found for historical replay."
            trace.stages.append(entry)
            continue

        commit = assigned.get(stage.stage_id)
        if commit is None:
            entry.skipped_reason = "No matching commit in git history for this stage."
            trace.stages.append(entry)
            continue

        entry.commit = commit
        try:
            entry.report = _audit_commit(repo, commit.sha, home)
            for sid in entry.report.session_ids:
                all_sessions.add(sid)
        except Exception as exc:  # noqa: BLE001
            entry.skipped_reason = f"Audit failed: {exc}"

        trace.stages.append(entry)

    trace.session_ids = sorted(all_sessions)
    return trace
