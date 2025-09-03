from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
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

_ensure_sqlite_parent_dir(settings.DATABASE_URL)

engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
