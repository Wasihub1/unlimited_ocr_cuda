"""Start model loading in the lifespan without blocking readiness polling."""
import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT
from app.routes.api import router
from app.model_loader import service


@asynccontextmanager
async def lifespan(app):
    loading = asyncio.create_task(asyncio.to_thread(service.initialize))
    try:
        yield
    finally:
        await loading
        from app.routes.api import wait_for_jobs
        await asyncio.to_thread(wait_for_jobs)

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Unlimited-OCR Test UI", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.middleware("http")
async def fresh_frontend(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        # This local test UI changes frequently; keep HTML and JS in sync.
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "frontend" / "index.html")
