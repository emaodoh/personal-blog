import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from routers import web, api
from routers.auth import initialize_admin_auth
from routers.services import initialize_database


PROJECT_ROOT = Path(__file__).resolve().parent


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


async def not_found(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=404)

    return web.templates.TemplateResponse(
        request=request,
        name="404.html",
        status_code=404,
    )


def create_app():

    app = FastAPI(
        title="Personal blog page",
        debug=_env_bool("APP_DEBUG", False),
    )

    initialize_database()
    initialize_admin_auth()
    app.add_exception_handler(404, not_found)

    app.mount(
        "/static",
        StaticFiles(directory=PROJECT_ROOT / "static"),
        name="static",
    )
    app.include_router(api.router, prefix="/api", tags=["REST API"])
    app.include_router(web.router, tags=["Web Pages"])

    return app

app = create_app()
