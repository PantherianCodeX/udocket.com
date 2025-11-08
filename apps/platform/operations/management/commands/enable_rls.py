# pyright: strict

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection, transaction

TABLES_TO_ENABLE = (
    "cases_case",
    "cases_casemembership",
    "jobs_job",
    "artifacts_caseartifact",
)

POLICIES = (
    (
        "public",
        "cases_case",
        "case_org_isolation",
        "CREATE POLICY case_org_isolation ON cases_case USING "
        "(organization_id::text = current_setting('app.current_organization', true));",
    ),
    (
        "public",
        "cases_casemembership",
        "casemem_org_isolation",
        "CREATE POLICY casemem_org_isolation ON cases_casemembership USING "
        "(case_id IN (SELECT id FROM cases_case "
        "WHERE organization_id::text = current_setting('app.current_organization', true)));",
    ),
    (
        "public",
        "jobs_job",
        "jobs_org_isolation",
        "CREATE POLICY jobs_org_isolation ON jobs_job USING "
        "(organization_id::text = current_setting('app.current_organization', true));",
    ),
    (
        "public",
        "artifacts_caseartifact",
        "artifacts_org_isolation",
        "CREATE POLICY artifacts_org_isolation ON artifacts_caseartifact USING "
        "(organization_id::text = current_setting('app.current_organization', true));",
    ),
)


class Command(BaseCommand):
    help = "Enable and configure Postgres row-level security for multi-tenancy."

    def handle(self, *args: Any, **options: Any) -> None:
        vendor = connection.vendor
        if vendor != "postgresql":
            self.stdout.write(self.style.WARNING("RLS not applied: database is not PostgreSQL."))
            return
        with transaction.atomic():
            with connection.cursor() as cur:
                for table in TABLES_TO_ENABLE:
                    cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")

                for schema, table, policy, create_sql in POLICIES:
                    cur.execute(
                        (
                            "SELECT 1 FROM pg_policies "
                            "WHERE schemaname=%s AND tablename=%s AND policyname=%s"
                        ),
                        [schema, table, policy],
                    )
                    if cur.fetchone():
                        continue
                    cur.execute(create_sql)
        self.stdout.write(
            self.style.SUCCESS("RLS enabled/updated for cases, memberships, jobs, and artifacts.")
        )
