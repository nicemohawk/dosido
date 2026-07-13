import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.backfill_worker import run_backfill_worker
from app.redis_client import close_pool
from app.round_monitor import run_round_monitor
from app.routes.admin_api import router as admin_router
from app.routes.public_api import router as public_router
from app.routes.signal_api import router as signal_router
from app.routes.views import router as views_router

APP_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks: walk-up scoring backfill + round timer monitor
    background_tasks = [
        asyncio.create_task(run_backfill_worker()),
        asyncio.create_task(run_round_monitor()),
    ]
    yield
    for task in background_tasks:
        task.cancel()
        try:
            await task
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


_NOT_FOUND_PAGE = (APP_DIR / "templates" / "404.html").read_text()


@app.exception_handler(StarletteHTTPException)
async def custom_404(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(_NOT_FOUND_PAGE, status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


# View routes (catch-all slug patterns — register last)
app.include_router(views_router)
