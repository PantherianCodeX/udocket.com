# Activation Checklist

| Step | Description | Command/Evidence | Status |
|------|-------------|------------------|--------|
| 1 | Refresh readiness datasets | `python -m packages.devops.readiness.cli refresh` | pending |
| 2 | Validate LangSmith eval export | `python scripts/langsmith/export_results.py` | pending |
| 3 | LangFuse enable + disable evidence | `reports/langfuse_enable_disable.md` entries | pending |
| 4 | Migration backlog verified | `data/backlog/migration_backlog.json` hash matches readiness | pending |
| 5 | Activation sign-off recorded | `reports/activation_signoff.md` | pending |
