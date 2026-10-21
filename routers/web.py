from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .auth import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_MAX_AGE_SECONDS,
    authenticate_admin,
    clear_login_failures,
    create_admin_session,
    delete_admin_session,
    get_admin_session_username,
    is_login_rate_limited,
    record_login_failure,
    require_admin,
    validate_csrf_token,
)
from .services import (
    add_article,
    delete_article,
    edit_article,
    get_connection,
    get_article_by_id,
    load_article,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")

router = APIRouter()


@router.get("/")
def home(request: Request):
    articles = load_article()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"articles": articles},
    )


@router.get("/article/{article_id}")
def blog(article_id: int, request: Request):
    try:
        article = get_article_by_id(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    word_count = len(article["content"].split())
    reading_time = max(1, round(word_count / 220))
    return templates.TemplateResponse(
        request=request,
        name="blog.html",
        context={"article": article, "reading_time": reading_time},
    )


@router.get("/admin_dashboard")
def admin_dashboard(request: Request, admin_session: dict = Depends(require_admin)):
    articles = load_article()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "articles": articles,
            "csrf_token": admin_session["csrf_token"],
        },
    )


@router.post("/delete_blog/{article_id}")
def delete_blog(
    request: Request,
    article_id: int,
    csrf_token: str = Form(...),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)

    try:
        delete_article(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.get("/edit_blog/{article_id}")
def edit_blog(
    article_id: int,
    request: Request,
    admin_session: dict = Depends(require_admin),
):
    try:
        article = get_article_by_id(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "article": article,
            "csrf_token": admin_session["csrf_token"],
        },
    )


@router.post("/edit_blog/{article_id}")
def edit_blog(
    request: Request,
    article_id: int,
    title: str = Form(),
    content: str = Form(),
    summary: str = Form(),
    csrf_token: str = Form(...),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)

    try:
        edit_article(article_id, title, content, summary)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RedirectResponse(url=f"/edit_blog/{article_id}", status_code=303)


@router.get("/login")
def login(request: Request):
    if get_admin_session_username(request.cookies.get(SESSION_COOKIE_NAME)):
        return RedirectResponse(url="/admin_dashboard", status_code=303)

    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if is_login_rate_limited(request, username):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "flash": {
                    "category": "error",
                    "message": "Too many failed attempts. Try again later.",
                }
            },
            status_code=429,
        )

    authenticated_username = authenticate_admin(username, password)
    if authenticated_username is None:
        record_login_failure(request, username)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "flash": {
                    "category": "error",
                    "message": "Invalid username or password.",
                }
            },
            status_code=401,
        )

    clear_login_failures(request, username)
    token = create_admin_session(authenticated_username)
    response = RedirectResponse(url="/admin_dashboard", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/logout")
def logout(request: Request):
    delete_admin_session(request.cookies.get(SESSION_COOKIE_NAME))

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/add_blog")
def add_blog(request: Request, admin_session: dict = Depends(require_admin)):
    return templates.TemplateResponse(
        request=request,
        name="add_blog.html",
        context={"csrf_token": admin_session["csrf_token"]},
    )


@router.post("/add_blog")
def add_blog(
    request: Request,
    title: str = Form(),
    content: str = Form(),
    summary: str = Form(),
    csrf_token: str = Form(...),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)

    add_article(title, content, summary)
    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.get("/health")
def health():
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except Exception:
        return JSONResponse(
            {"status": "error", "database": "unavailable"},
            status_code=503,
        )

    return {"status": "ok", "database": "ok"}
