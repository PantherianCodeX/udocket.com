from fastapi import FastAPI
from apps.api.app.routers import transcriptions, cases
from db.session import engine
from db.base import Base

app = FastAPI(title="uDocket API", version="0.1.0")

# MVP: create tables (SQLite). For Postgres prod, use Alembic migrations only.
Base.metadata.create_all(bind=engine)

app.include_router(cases.router, prefix="/cases", tags=["cases"])
app.include_router(transcriptions.router, prefix="/transcriptions", tags=["transcriptions"])

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/health/ready")
def ready():
    return {"status": "ready"}