"""Git commit window and diff analysis."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ccer.models.git import CommitInfo, FileChange, GitActivity


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _parse_commit(repo: Path, ref: str) -> CommitInfo | None:
    try:
        fmt = "%H|%h|%s|%b|%an|%cI"
        line = _run_git(repo, "log", "-1", f"--format={fmt}", ref).strip()
    except subprocess.CalledProcessError:
        return None
    parts = line.split("|", 5)
    if len(parts) < 6:
        return None
    sha, short, subject, body, author, committed = parts
    parent = None
    try:
        parent = _run_git(repo, "rev-parse", f"{sha}^").strip()
    except subprocess.CalledProcessError:
        parent = None
    subject_l = subject.lower()
    return CommitInfo(
        sha=sha,
        short_sha=short,
        subject=subject,
        body=body.strip(),
        author_name=author,
        committed_at=datetime.fromisoformat(committed.replace("Z", "+00:00")),
        parent_sha=parent,
        is_revert=subject_l.startswith("revert ") or "revert" in subject_l[:20],
    )


def analyze_commit(repo_path: Path, commit: str = "HEAD") -> GitActivity:
    repo = repo_path.resolve()
    commit_info = _parse_commit(repo, commit)
    if commit_info is None:
        raise ValueError(f"Commit not found: {commit}")

    parent_info = None
    if commit_info.parent_sha:
        parent_info = _parse_commit(repo, commit_info.parent_sha)
        window_start = parent_info.committed_at if parent_info else commit_info.committed_at
    else:
        window_start = datetime.fromtimestamp(0, tz=timezone.utc)

    window_end = commit_info.committed_at

    diff_range = f"{commit_info.parent_sha}..{commit_info.sha}" if commit_info.parent_sha else commit_info.sha
    try:
        diff_stat = _run_git(repo, "diff", diff_range, "--stat")
        diff_patch = _run_git(repo, "diff", diff_range)
        numstat = _run_git(repo, "diff", diff_range, "--numstat").strip()
    except subprocess.CalledProcessError:
        diff_stat = _run_git(repo, "show", commit_info.sha, "--stat")
        diff_patch = _run_git(repo, "show", commit_info.sha, "--format=")
        numstat = _run_git(repo, "show", commit_info.sha, "--numstat").strip()

    files: list[FileChange] = []
    total_ins = total_del = 0
    tests_touched: list[str] = []
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        ins_s, del_s, path = parts[0], parts[1], parts[2]
        if ins_s == "-" or del_s == "-":
            continue
        ins, dels = int(ins_s), int(del_s)
        files.append(FileChange(path=path, insertions=ins, deletions=dels))
        total_ins += ins
        total_del += dels
        if "test" in path.lower():
            tests_touched.append(path)

    return GitActivity(
        commit=commit_info,
        parent=parent_info,
        window_start=window_start.astimezone(timezone.utc),
        window_end=window_end.astimezone(timezone.utc),
        files=files,
        total_insertions=total_ins,
        total_deletions=total_del,
        net_lines=total_ins - total_del,
        diff_stat=diff_stat.strip(),
        diff_patch=diff_patch[:12000],
        tests_touched=tests_touched,
    )
