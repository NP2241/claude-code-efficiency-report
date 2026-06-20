# CCER Reports

Generated Markdown reports from `ccer audit` and `ccer scenario`, committed here for demos and review.

| Path | Contents |
|------|----------|
| `claude-expense-tracker/` | Dogfood test app — per-commit audits + full scenario trace |

Reports are written here (not into the audited repo's `.ccer/`) so they can be versioned in this project.

Regenerate:

```bash
ccer scenario --repo ~/Downloads/claude-expense-tracker
ccer audit --repo ~/Downloads/claude-expense-tracker --commit HEAD
```
