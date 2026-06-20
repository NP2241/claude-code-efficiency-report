"""Parse Claude Code session JSONL transcripts."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ccer.models.usage import ModelBreakdown, ModelSwitch, SessionSummary, UsageSummary
from ccer.parsers.pricing import estimate_cost_usd


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except ValueError:
        return None


def _repo_matches(cwd: str | None, repo_path: Path) -> bool:
    if not cwd:
        return False
    try:
        cwd_path = Path(cwd).resolve()
        repo = repo_path.resolve()
        return cwd_path == repo or repo in cwd_path.parents
    except OSError:
        return False


def _extract_usage(row: dict) -> tuple[str, str, dict] | None:
    if row.get("type") != "assistant":
        return None
    message = row.get("message") or {}
    usage = message.get("usage")
    if not usage:
        return None
    request_id = row.get("requestId") or message.get("id")
    if not request_id:
        return None
    model = message.get("model") or "unknown"
    return str(request_id), model, usage


def _usage_counts(usage: dict) -> tuple[int, int, int, int]:
    return (
        int(usage.get("input_tokens") or 0),
        int(usage.get("output_tokens") or 0),
        int(usage.get("cache_read_input_tokens") or 0),
        int(usage.get("cache_creation_input_tokens") or 0),
    )


def _iter_jsonl(paths: list[Path]):
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _collect_paths(project_dir: Path) -> list[Path]:
    paths = sorted(project_dir.glob("*.jsonl"))
    paths.extend(sorted(project_dir.glob("*/subagents/*.jsonl")))
    return paths


def read_transcripts(
    project_dir: Path,
    repo_path: Path,
    window_start: datetime,
    window_end: datetime,
) -> UsageSummary:
    paths = _collect_paths(project_dir)
    if not paths:
        return UsageSummary(
            data_source="transcripts",
            warnings=["No transcript JSONL files found for this repo."],
        )

    seen: set[str] = set()
    turns: list[dict] = []
    session_meta: dict[str, dict] = defaultdict(
        lambda: {"tokens": 0, "started_at": None, "ended_at": None, "entrypoint": None}
    )

    for row in _iter_jsonl(paths):
        ts = _parse_ts(row.get("timestamp"))
        if ts is None or ts < window_start or ts > window_end:
            continue
        if not _repo_matches(row.get("cwd"), repo_path):
            continue

        session_id = row.get("sessionId") or "unknown"
        meta = session_meta[session_id]
        if meta["started_at"] is None or ts < meta["started_at"]:
            meta["started_at"] = ts
        if meta["ended_at"] is None or ts > meta["ended_at"]:
            meta["ended_at"] = ts
        if row.get("entrypoint"):
            meta["entrypoint"] = row.get("entrypoint")

        extracted = _extract_usage(row)
        if not extracted:
            continue
        request_id, model, usage = extracted
        if request_id in seen:
            continue
        seen.add(request_id)

        inp, out, cache_read, cache_create = _usage_counts(usage)
        total = inp + out + cache_read + cache_create
        meta["tokens"] += total
        turns.append(
            {
                "at": ts,
                "session_id": session_id,
                "model": model,
                "input_tokens": inp,
                "output_tokens": out,
                "cache_read_tokens": cache_read,
                "cache_creation_tokens": cache_create,
                "total_tokens": total,
            }
        )

    by_model: dict[str, ModelBreakdown] = {}
    for turn in turns:
        mb = by_model.setdefault(
            turn["model"],
            ModelBreakdown(model=turn["model"]),
        )
        mb.input_tokens += turn["input_tokens"]
        mb.output_tokens += turn["output_tokens"]
        mb.cache_read_tokens += turn["cache_read_tokens"]
        mb.cache_creation_tokens += turn["cache_creation_tokens"]
        mb.turn_count += 1
        mb.estimated_cost_usd += estimate_cost_usd(
            turn["model"],
            turn["input_tokens"],
            turn["output_tokens"],
            turn["cache_read_tokens"],
            turn["cache_creation_tokens"],
        )

    switches: list[ModelSwitch] = []
    tokens_before = 0
    prev_model: str | None = None
    for turn in sorted(turns, key=lambda t: t["at"]):
        if prev_model and turn["model"] != prev_model:
            switches.append(
                ModelSwitch(
                    at=turn["at"],
                    from_model=prev_model,
                    to_model=turn["model"],
                    tokens_before_switch=tokens_before,
                )
            )
        prev_model = turn["model"]
        tokens_before += turn["total_tokens"]

    sessions = [
        SessionSummary(
            session_id=sid,
            started_at=meta["started_at"],
            ended_at=meta["ended_at"],
            tokens=meta["tokens"],
            entrypoint=meta["entrypoint"],
        )
        for sid, meta in session_meta.items()
        if meta["tokens"] > 0
    ]

    total_tokens = sum(t["total_tokens"] for t in turns)
    total_cost = sum(m.estimated_cost_usd for m in by_model.values())

    return UsageSummary(
        total_tokens=total_tokens,
        estimated_cost_usd=round(total_cost, 4),
        session_count=len(sessions),
        turn_count=len(turns),
        tokens_by_model=sorted(by_model.values(), key=lambda m: -m.total_tokens),
        model_switches=switches,
        sessions=sessions,
        data_source="transcripts",
    )


def read_token_total_override(token_total: int) -> UsageSummary:
    return UsageSummary(
        total_tokens=token_total,
        estimated_cost_usd=0.0,
        session_count=0,
        turn_count=0,
        data_source="token_total",
        warnings=["Limited usage data — cost estimate only; no model breakdown."],
    )
