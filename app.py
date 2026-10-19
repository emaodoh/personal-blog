from fastapi import FastAPI
from routers import web, api
from fastapi.staticfiles import StaticFiles


def create_app():

    app = FastAPI(title="Personal blog page")



    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(api.router, prefix="/api", tags=["REST API"])
    app.include_router(web.router, tags=["Web Pages"])

    return app

app = create_app()