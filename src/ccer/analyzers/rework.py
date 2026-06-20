"""Heuristic rework detection for single-commit audits."""

from __future__ import annotations

import re

from ccer.models.git import GitActivity
from ccer.models.report import ReworkFlag

FIX_PATTERN = re.compile(r"\bfix\b", re.I)


def detect_rework(git: GitActivity) -> list[ReworkFlag]:
    flags: list[ReworkFlag] = []
    subject = git.commit.subject
    body = git.commit.body

    if FIX_PATTERN.search(subject) or FIX_PATTERN.search(body):
        flags.append(
            ReworkFlag(
                rule_id="FIX_KEYWORD",
                severity="medium",
                message="Commit message indicates a fix or follow-up correction.",
                evidence=f"Subject: {subject}",
            )
        )

    if git.commit.is_revert or subject.lower().startswith("revert"):
        flags.append(
            ReworkFlag(
                rule_id="REVERT",
                severity="high",
                message="Commit reverts prior work — likely wasted AI spend.",
                evidence=f"Subject: {subject}",
            )
        )

    for fc in git.files:
        if fc.insertions >= 80 and fc.deletions >= 80:
            flags.append(
                ReworkFlag(
                    rule_id="ADD_DELETE_SPIKE",
                    severity="medium",
                    message=f"Large add+delete spike on {fc.path}.",
                    evidence=f"+{fc.insertions}/-{fc.deletions} lines",
                )
            )
        elif fc.insertions + fc.deletions >= 120 and min(fc.insertions, fc.deletions) > 20:
            flags.append(
                ReworkFlag(
                    rule_id="FILE_CHURN",
                    severity="low",
                    message=f"Heavy churn within commit on {fc.path}.",
                    evidence=f"+{fc.insertions}/-{fc.deletions} lines",
                )
            )

    return flags
