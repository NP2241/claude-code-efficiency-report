# Claude Code Efficiency Report

Evidence-backed reports correlating Claude token usage with git activity, rework patterns, and engineering efficiency — built for a YC demo targeting **July 27**.

## Demo scope (v0)

1. **Report input** — engineer, repo, date range, usage file or token total
2. **Usage parser** — tokens, cost, sessions, daily breakdown
3. **Git diff analyzer** — commits, files, lines, PRs, tests
4. **Rework detector** — fix commits, reverts, file churn, etc.
5. **Generated report** — manager-facing Markdown/HTML with efficiency score and budget recommendation

## Documentation

See **[PROPOSAL.md](./PROPOSAL.md)** for the full technical proposal: architecture, module design, data models, implementation timeline, and post-demo roadmap.

## Quick start (coming soon)

```bash
cd claude-code-efficiency-report
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn ccer.main:app --reload
```

## Project layout

```
src/ccer/          # Application code
tests/             # Unit tests + fixtures
scripts/           # Demo helpers
```

## Status

**Planning phase** — proposal complete; implementation not yet started.
