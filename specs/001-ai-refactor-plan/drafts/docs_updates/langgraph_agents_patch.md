```diff
@@ docs/automation/langgraph-agents.md:8.3
-- Runbooks must cover activation rollback, shadow divergence, and QA defect surge.
+- Runbooks must cover activation rollback, shadow divergence, QA defect surge, and the LangSmith/LangFuse workflows defined in specs/001-ai-refactor-plan/reports/.
+- LangSmith evaluation ingest steps: reference packages/devops/readiness CLI, evidence files (reports/langsmith_workspace_records.jsonl, reports/langsmith_eval_export.json, reports/langsmith_smoke.jsonl).
+- LangFuse R&D enablement: cite reports/langfuse_enable_disable.md and the 15-minute disable SLA.
```

```diff
@@ docs/overview/tdd/appendices/repository_trees.md
- spec/
+ schemas/
  specs/
+ automation/
+   pipelines/
+     analyze_modernization.yaml
+     compose_release.yaml
```
