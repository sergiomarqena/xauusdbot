from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Research-first gold market intelligence. Demo data is explicitly labelled; no trade execution.",
)
app.include_router(router)

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")
