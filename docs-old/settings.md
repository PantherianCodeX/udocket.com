# uDocket Settings Architecture

The platform now uses a single Pydantic-powered settings module (`config/settings.py`) to provide a typed, centralized source of configuration for Django, background workers, and agent libraries. The settings loader understands multiple input channels, applies validation, and exposes structured views that downstream code can consume without re-parsing environment variables.

## Loading order and secrets support

1. **Environment variables** remain the primary source of truth. All historical variable names are preserved for backwards compatibility. Validation is applied before the values become available to the rest of the system, preventing drift between services.
2. **`*_FILE` fallbacks**: when an environment variable is absent, the loader automatically reads from a sibling variable that ends with `_FILE` (e.g., `DJANGO_SECRET_KEY_FILE`). The referenced file content is trimmed and treated as the value for the base variable. This pattern matches Docker and Kubernetes secret projections.
3. **Secrets directories**: set `UDOCKET_SECRETS_DIR` (or the generic `SECRETS_DIR`) to point at a directory that contains secret files. The loader will scan the directory for filenames that match the expected setting names (case insensitive) and use their contents when the corresponding environment variable is not present.
4. **`.env` files**: pass `UDOCKET_ENV_FILE` to specify an explicit file, or export `ENV_READ_DOTENV=1` to opt-in to loading the repository’s `.env` file when present. This keeps production-safe defaults while enabling local overrides.

## Structured accessors

The `Settings` object exposes strongly typed sections that consolidate related concerns:

- `settings.azure` groups Speech and Blob configuration with helper methods that unwrap secrets.
- `settings.storage` ensures the storage root exists (falling back to `./storage` when necessary) and exposes helper paths.
- `settings.database` produces Django-ready configurations and performs availability checks before falling back to SQLite.
- `settings.django`, `settings.celery`, `settings.redis`, `settings.logging`, `settings.jobs_ui`, and `settings.oidc` each provide view objects that the Django runtime imports directly, eliminating duplicated parsing logic.

During initialization, the loader performs basic misconfiguration checks—such as enforcing the organization’s Azure region allowlist and refusing to boot with the development Django secret key when `DJANGO_DEBUG` is disabled—so failures surface early.

## Security considerations: environment variables vs. secret files

Both transport mechanisms can be secure when managed correctly, but they trade different risks:

- **Environment variables** are inherited by child processes, captured in crash dumps, and typically exposed via process inspection tooling. They are easy to inject through container orchestrators and CI/CD pipelines but require strict controls to avoid leakage into logs or diagnostic output.
- **Secret files** can be mounted with restrictive POSIX permissions, rotated atomically, and consumed without polluting process environments. They work well with Docker/Kubernetes secrets and satisfy platforms that forbid long-lived secrets in environment variables. However, file-based secrets must be stored on encrypted volumes, and care must be taken to prevent them from being baked into container images or included in backups inadvertently.

By supporting both styles—and preferring files whenever they are provided—the new loader enables a “defense in depth” approach. Operators can keep day-to-day configuration in the environment while serving high-sensitivity credentials (Azure keys, database passwords, OAuth secrets) from dedicated secret stores.
