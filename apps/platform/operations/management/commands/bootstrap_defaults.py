# pyright: strict

from __future__ import annotations

from dataclasses import replace
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.platform.operations.bootstrap import (
    BootstrapConfig,
    BootstrapSummary,
    OrganizationConfig,
    SuperuserConfig,
    bootstrap_stack,
)


class Command(BaseCommand):
    help = (
        "Bootstrap the local platform using environment defaults (superuser, organization, presets). "
        "Set PLATFORM_BOOTSTRAP_ENABLED=1 to run automatically or pass --force for a one-off execution."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore PLATFORM_BOOTSTRAP_ENABLED and run bootstrap steps once.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        config = BootstrapConfig.from_env()
        force = bool(options.get("force"))
        if force and not config.enabled:
            config = replace(config, enabled=True)

        if not config.enabled:
            self.stdout.write(
                self.style.WARNING(
                    "Bootstrap disabled (PLATFORM_BOOTSTRAP_ENABLED not set). Skipping setup."
                )
            )
            return

        summary = bootstrap_stack(config)
        self._log_superuser(config.superuser, summary)
        self._log_organization(config.organization, summary)
        self._log_presets(summary)
        self.stdout.write(self.style.SUCCESS("Bootstrap complete."))

    def _log_superuser(self, config: SuperuserConfig | None, summary: BootstrapSummary) -> None:
        if config is None:
            self.stdout.write("Superuser creation skipped (DJANGO_SUPERUSER_* not fully defined).")
            return
        if summary.superuser_created:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{config.username}' created."))
        elif summary.superuser_updated:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{config.username}' updated."))
        else:
            self.stdout.write(f"Superuser '{config.username}' already up to date.")

    def _log_organization(
        self, config: OrganizationConfig | None, summary: BootstrapSummary
    ) -> None:
        if config is None:
            self.stdout.write("Organization bootstrap skipped (no configuration found).")
            return
        if summary.organization_created:
            self.stdout.write(self.style.SUCCESS(f"Organization '{config.name}' created."))
        elif summary.organization_updated:
            self.stdout.write(self.style.SUCCESS(f"Organization '{config.name}' updated."))
        else:
            self.stdout.write(f"Organization '{config.name}' already up to date.")

        if summary.membership_created:
            self.stdout.write(self.style.SUCCESS("Attached superuser membership to organization."))
        elif summary.membership_updated:
            self.stdout.write(self.style.SUCCESS("Updated superuser organization membership."))

    def _log_presets(self, summary: BootstrapSummary) -> None:
        if summary.presets_imported:
            self.stdout.write(self.style.SUCCESS("Permission presets imported."))
        else:
            self.stdout.write("Permission presets import skipped.")
