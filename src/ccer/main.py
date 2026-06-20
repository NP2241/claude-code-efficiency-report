"""CCER audit pipeline and CLI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ccer.analyzers.git import analyze_commit
from ccer.discovery.claude_home import claude_project_dir
from ccer.models.input import AuditRequest
from ccer.parsers.transcripts import read_token_total_override, read_transcripts
from ccer.reports.generator import ReportGenerator, build_report
from ccer.scenario.trace import build_scenario_trace


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _git_user_name(repo: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        return r.stdout.strip() or None
    except subprocess.CalledProcessError:
        return None


def run_audit(request: AuditRequest) -> Path:
    repo = request.repo_path.resolve()
    git = analyze_commit(repo, request.commit)

    if request.token_total is not None:
        usage = read_token_total_override(request.token_total)
    else:
        project_dir = claude_project_dir(repo, request.claude_home)
        if project_dir is None:
            usage = read_transcripts(Path("/nonexistent"), repo, git.window_start, git.window_end)
            usage.warnings.append(
                f"No Claude transcripts at ~/.claude/projects/ for {repo}. "
                "Use --token-total or --usage-file as fallback."
            )
        else:
            usage = read_transcripts(project_dir, repo, git.window_start, git.window_end)
            if usage.total_tokens == 0 and not usage.warnings:
                usage.warnings.append(
                    "No token usage in commit time window — commit may predate Claude work "
                    "or cwd did not match repo."
                )

    report = build_report(usage, git)
    gen = ReportGenerator()
    return gen.render(report, repo)


def cmd_audit(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve() if args.repo else _repo_root()
    req = AuditRequest(
        repo_path=repo,
        commit=args.commit,
        engineer_name=args.author or _git_user_name(repo),
        claude_home=Path(args.claude_dir).expanduser() if args.claude_dir else Path.home() / ".claude",
        token_total=args.token_total,
        usage_file=Path(args.usage_file).expanduser() if args.usage_file else None,
    )
    md_path = run_audit(req)
    print(f"Report: {md_path}")
    return 0


def cmd_scenario(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve() if args.repo else _repo_root()
    claude_home = Path(args.claude_dir).expanduser() if args.claude_dir else Path.home() / ".claude"
    trace = build_scenario_trace(repo, claude_home=claude_home)
    gen = ReportGenerator()
    md_path = gen.render_scenario(trace)
    print(f"Scenario report: {md_path}")
    print(f"  Stages: {len(trace.stages)} · Audited: {trace.audited_commits}")
    print(f"  Total tokens: {trace.total_tokens:,} · Est. cost: ${trace.total_cost_usd:.4f}")
    return 0


def cmd_init(_args: argparse.Namespace) -> int:
    repo = _repo_root()
    hook = repo / ".git" / "hooks" / "post-commit"
    script = (
        "#!/bin/sh\n"
        "ccer audit 2>/dev/null || true\n"
    )
    hook.write_text(script, encoding="utf-8")
    hook.chmod(0o755)
    project = claude_project_dir(repo)
    print(f"Post-commit hook installed: {hook}")
    if project:
        print(f"Claude transcripts: {project}")
    else:
        print("Claude project dir not found yet — open Claude Code in this repo once.")
    return 0


def cli() -> None:
    parser = argparse.ArgumentParser(prog="ccer", description="Claude Code Efficiency Report")
    sub = parser.add_subparsers(dest="command", required=True)

    audit_p = sub.add_parser("audit", help="Audit last commit (or --commit SHA)")
    audit_p.add_argument("--commit", default="HEAD", help="Commit ref to audit")
    audit_p.add_argument("--repo", help="Repo path (default: git root)")
    audit_p.add_argument("--author", help="Engineer name override")
    audit_p.add_argument("--claude-dir", help="Override ~/.claude")
    audit_p.add_argument("--token-total", type=int, help="Manual token total fallback")
    audit_p.add_argument("--usage-file", help="Manual usage JSONL fallback")
    audit_p.set_defaults(func=cmd_audit)

    scenario_p = sub.add_parser(
        "scenario",
        help="Full dogfood scenario trace — all stages in one Markdown report",
    )
    scenario_p.add_argument("--repo", help="Repo path (default: git root)")
    scenario_p.add_argument("--claude-dir", help="Override ~/.claude")
    scenario_p.set_defaults(func=cmd_scenario)

    init_p = sub.add_parser("init", help="Install post-commit hook")
    init_p.set_defaults(func=cmd_init)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    cli()
