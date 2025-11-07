from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings


def _ensure_sqlite_parent_dir(db_url: str):
    # Handle file-based SQLite URLs only
    if not db_url.startswith("sqlite:"):
        return
    # Skip in-memory or URI modes
    if db_url in ("sqlite://", "sqlite:///:memory:") or db_url.endswith(":memory:"):
        return
    # Normalize path part
    path_part = None
    if db_url.startswith("sqlite:////"):
        # Absolute
        path_part = db_url.replace("sqlite:////", "/", 1)
    elif db_url.startswith("sqlite:///"):
        # Relative to CWD
        path_part = db_url.replace("sqlite:///", "", 1)
    if not path_part:
        return
    p = Path(path_part)
    if not p.is_absolute():
        p = Path.cwd() / p
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Let SQLAlchemy raise the original error if we fail here
        pass


db_config = settings.database
_ensure_sqlite_parent_dir(db_config.url)

engine = create_engine(db_config.url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ensure_jobs_schema():
    # Add new columns to jobs table on existing SQLite DBs without Alembic.
    try:
        if not db_config.url.startswith("sqlite:"):
            return
        with engine.begin() as conn:
            # If table doesn't exist yet, nothing to do; create_all will create with new columns
            exists = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'",
            ).fetchone()
            if not exists:
                return
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(jobs)").fetchall()}
            want = {
                "audio_bytes": "INTEGER",
                "audio_mime": "VARCHAR(128)",
                "audio_ext": "VARCHAR(16)",
                "audio_mtime": "DATETIME",
                "transcript_words": "INTEGER",
                "transcript_bytes": "INTEGER",
                "audio_bitrate_kbps": "INTEGER",
                "audio_channels": "INTEGER",
                "audio_duration_sec": "INTEGER",
                "sample_rate_hz": "INTEGER",
                "diagnostics": "BOOLEAN",
            }
            for name, ddl in want.items():
                if name not in cols:
                    conn.exec_driver_sql(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}")
    except Exception:
        # Best-effort; skip on failure
        pass


def ensure_cases_schema():
    # Add new columns to cases table on existing SQLite DBs without Alembic.
    try:
        if not db_config.url.startswith("sqlite:"):
            return
        with engine.begin() as conn:
            exists = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='cases'",
            ).fetchone()
            if not exists:
                return
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(cases)").fetchall()}
            if "client_role" not in cols:
                conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN client_role VARCHAR(20)")
            if "updated_at" not in cols:
                conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN updated_at DATETIME")
    except Exception:
        pass
