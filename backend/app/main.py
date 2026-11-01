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

# Railway builds from /backend, so the repo-level frontend is outside the image.
# Prefer a bundled backend/frontend copy; retain repo-root fallback for local/full-repo runs.
_APP_DIR = Path(__file__).resolve().parent
_FRONTEND_CANDIDATES = [
    _APP_DIR.parent / "frontend",
    _APP_DIR.parents[1] / "frontend",
]
FRONTEND_DIR = next((path for path in _FRONTEND_CANDIDATES if path.is_dir()), None)

if FRONTEND_DIR is not None:
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}


@app.get("/", include_in_schema=False)
async def dashboard():
    if FRONTEND_DIR is not None and (FRONTEND_DIR / "index.html").is_file():
        return FileResponse(FRONTEND_DIR / "index.html")
    return {"status": "ok", "service": settings.app_name, "detail": "frontend not bundled"}
