import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.backfill_worker import run_backfill_worker
from app.redis_client import close_pool
from app.routes.admin_api import router as admin_router
from app.routes.public_api import router as public_router
from app.routes.signal_api import router as signal_router
from app.routes.views import router as views_router

APP_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start backfill worker as a background task
    backfill_task = asyncio.create_task(run_backfill_worker())
    yield
    backfill_task.cancel()
    try:
        await backfill_task
    except asyncio.CancelledError:
        pass
    await close_pool()


app = FastAPI(title="Dosido", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


@app.middleware("http")
async def filling(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Filling"] = "peanut-butter"
    return response


# API routes (must be registered before view routes to avoid slug capture)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(signal_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def custom_404(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        page = (APP_DIR / "templates" / "404.html").read_text()
        return HTMLResponse(page, status_code=404)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)


# View routes (catch-all slug patterns — register last)
app.include_router(views_router)
