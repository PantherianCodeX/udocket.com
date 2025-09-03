from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apps.admin.app.routers import dashboard, cases, uploads
from db.session import engine, ensure_jobs_schema
from db.base import Base

app = FastAPI(title="uDocket Admin", version="0.1.0")
Base.metadata.create_all(bind=engine)
ensure_jobs_schema()

app.include_router(dashboard.router)
app.include_router(cases.router)
app.include_router(uploads.router)
app.mount("/static", StaticFiles(directory="apps/admin/app/static"), name="static")

@app.get("/health/live")
def live():
    return {"status":"ok"}
