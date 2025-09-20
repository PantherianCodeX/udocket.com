from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection, transaction


POLICIES_SQL = [
    # Ensure extension namespace exists (no-op if already present)
    "",  # placeholder for readability
    # Cases
    "ALTER TABLE cases_case ENABLE ROW LEVEL SECURITY;",
    "CREATE POLICY IF NOT EXISTS case_org_isolation ON cases_case USING (organization_id::text = current_setting('app.current_organization', true));",
    # CaseMembership
    "ALTER TABLE cases_casemembership ENABLE ROW LEVEL SECURITY;",
    "CREATE POLICY IF NOT EXISTS casemem_org_isolation ON cases_casemembership USING (case_id IN (SELECT id FROM cases_case WHERE organization_id::text = current_setting('app.current_organization', true)));",
    # Jobs
    "ALTER TABLE jobs_job ENABLE ROW LEVEL SECURITY;",
    "CREATE POLICY IF NOT EXISTS jobs_org_isolation ON jobs_job USING (organization_id::text = current_setting('app.current_organization', true));",
    # Artifacts
    "ALTER TABLE artifacts_caseartifact ENABLE ROW LEVEL SECURITY;",
    "CREATE POLICY IF NOT EXISTS artifacts_org_isolation ON artifacts_caseartifact USING (organization_id::text = current_setting('app.current_organization', true));",
]


class Command(BaseCommand):
    help = "Enable and configure Postgres row-level security for multi-tenancy."

    def handle(self, *args, **options):  # type: ignore[override]
        vendor = connection.vendor
        if vendor != "postgresql":
            self.stdout.write(self.style.WARNING("RLS not applied: database is not PostgreSQL."))
            return
        with transaction.atomic():
            with connection.cursor() as cur:
                for stmt in POLICIES_SQL:
                    if not stmt.strip():
                        continue
                    cur.execute(stmt)
        self.stdout.write(self.style.SUCCESS("RLS enabled/updated for cases, memberships, jobs, and artifacts."))

