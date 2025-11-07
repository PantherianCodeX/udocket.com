# Task Modules

This package exposes the platform Celery task modules from
`apps.platform.operations.task_modules` so the new automation tree can be
imported without touching the legacy locations yet. Once the tasks migrate into
automation proper, this shim will vanish.

Refer to `docs/overview/tdd/appendices/repository_trees.md` for the binding
layout contract.
