from pathlib import Path
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
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
    get_article_by_id,
    load_article,
    load_projects,
    get_project_by_slug,
    save_project,
    delete_project,
    load_pages,
    save_page,
    load_settings,
    save_settings,
    upload_image,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")

router = APIRouter()


def _save_uploaded_image(upload, folder):
    extension = Path(upload.filename).suffix.lower()
    allowed = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp", ".gif": "gif"}
    if extension not in allowed:
        raise HTTPException(status_code=400, detail="Use a JPG, PNG, WebP, or GIF image.")
    image_data = upload.file.read(5 * 1024 * 1024 + 1)
    if len(image_data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Images must be 5 MB or smaller.")
    image_type = allowed[extension]
    valid_signature = (
        (image_type == "jpeg" and image_data.startswith(b"\xff\xd8\xff"))
        or (image_type == "png" and image_data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (image_type == "gif" and image_data[:6] in {b"GIF87a", b"GIF89a"})
        or (image_type == "webp" and image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP")
    )
    if not valid_signature:
        raise HTTPException(status_code=400, detail="The uploaded file is not a supported image.")
    filename = f"{secrets.token_hex(12)}{extension}"
    return upload_image(folder, filename, image_data, f"image/{image_type}")


@router.get("/")
def home(request: Request):
    articles = load_article(published_only=True)[:3]
    projects = load_projects(published_only=True, featured_only=True)[:3]
    pages = load_pages()
    settings = load_settings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"articles": articles, "projects": projects, "pages": pages, "settings": settings},
    )


@router.get("/blog")
def blog_index(request: Request):
    return templates.TemplateResponse(
        request=request, name="blog_index.html",
        context={"articles": load_article(published_only=True), "settings": load_settings()},
    )


@router.get("/article/{article_id}")
def blog(article_id: int, request: Request):
    try:
        article = get_article_by_id(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not article["is_published"]:
        raise HTTPException(status_code=404, detail="Article not found")

    word_count = len(article["content"].split())
    reading_time = max(1, round(word_count / 220))
    return templates.TemplateResponse(
        request=request,
        name="blog.html",
        context={"article": article, "reading_time": reading_time, "settings": load_settings()},
    )


@router.get("/projects")
def projects_index(request: Request):
    return templates.TemplateResponse(
        request=request, name="projects.html",
        context={"projects": load_projects(published_only=True), "settings": load_settings()},
    )


@router.get("/projects/{slug}")
def project_detail(slug: str, request: Request):
    try:
        project = get_project_by_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not project["is_published"]:
        raise HTTPException(status_code=404, detail="Project not found")
    return templates.TemplateResponse(
        request=request, name="project.html",
        context={"project": project, "settings": load_settings()},
    )


@router.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse(request=request, name="page.html", context={"page": load_pages()["about"], "settings": load_settings()})


@router.get("/contact")
def contact_page(request: Request):
    return templates.TemplateResponse(request=request, name="page.html", context={"page": load_pages()["contact"], "settings": load_settings()})


@router.get("/admin_dashboard")
def admin_dashboard(request: Request, admin_session: dict = Depends(require_admin)):
    articles = load_article()
    projects = load_projects()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "articles": articles,
            "projects": projects,
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
    is_published: str | None = Form(None),
    csrf_token: str = Form(...),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)

    try:
        edit_article(article_id, title, content, summary, is_published == "on")
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
    is_published: str | None = Form(None),
    csrf_token: str = Form(...),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)

    add_article(title, content, summary, is_published == "on")
    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.get("/admin/projects/new")
def new_project_page(request: Request, admin_session: dict = Depends(require_admin)):
    return templates.TemplateResponse(request=request, name="project_form.html", context={"project": None, "csrf_token": admin_session["csrf_token"]})


@router.post("/admin/projects/new")
def create_project(
    request: Request, title: str = Form(), summary: str = Form(""),
    description: str = Form(""), technologies: str = Form(""), image_url: str = Form(""),
    demo_url: str = Form(""), repository_url: str = Form(""),
    is_featured: str | None = Form(None), is_published: str | None = Form(None),
    csrf_token: str = Form(...), image_file: UploadFile | None = File(None),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)
    if image_file and image_file.filename:
        image_url = _save_uploaded_image(image_file, "projects")
    save_project(None, title, summary, description, technologies, image_url, demo_url,
                 repository_url, is_featured == "on", is_published == "on")
    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.get("/admin/projects/{project_id}/edit")
def edit_project_page(project_id: int, request: Request, admin_session: dict = Depends(require_admin)):
    project = next((item for item in load_projects() if item["id"] == project_id), None)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return templates.TemplateResponse(request=request, name="project_form.html", context={"project": project, "csrf_token": admin_session["csrf_token"]})


@router.post("/admin/projects/{project_id}/edit")
def update_project(
    project_id: int, request: Request, title: str = Form(), summary: str = Form(""),
    description: str = Form(""), technologies: str = Form(""), image_url: str = Form(""),
    demo_url: str = Form(""), repository_url: str = Form(""),
    is_featured: str | None = Form(None), is_published: str | None = Form(None),
    csrf_token: str = Form(...), image_file: UploadFile | None = File(None),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)
    if image_file and image_file.filename:
        image_url = _save_uploaded_image(image_file, "projects")
    try:
        save_project(project_id, title, summary, description, technologies, image_url,
                     demo_url, repository_url, is_featured == "on", is_published == "on")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.post("/admin/projects/{project_id}/delete")
def remove_project(project_id: int, request: Request, csrf_token: str = Form(...), _admin: dict = Depends(require_admin)):
    validate_csrf_token(request, csrf_token)
    try:
        delete_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.get("/admin/pages/{slug}")
def edit_page_form(slug: str, request: Request, admin_session: dict = Depends(require_admin)):
    page = load_pages().get(slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return templates.TemplateResponse(request=request, name="page_form.html", context={"page": page, "csrf_token": admin_session["csrf_token"]})


@router.post("/admin/pages/{slug}")
def update_page(slug: str, request: Request, title: str = Form(), content: str = Form(), csrf_token: str = Form(...), _admin: dict = Depends(require_admin)):
    validate_csrf_token(request, csrf_token)
    if slug not in {"home", "about", "contact"}:
        raise HTTPException(status_code=404, detail="Page not found")
    save_page(slug, title, content)
    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.get("/admin/settings")
def edit_settings_form(request: Request, admin_session: dict = Depends(require_admin)):
    return templates.TemplateResponse(request=request, name="settings_form.html", context={"settings": load_settings(), "csrf_token": admin_session["csrf_token"]})


@router.post("/admin/settings")
def update_settings(
    request: Request, site_name: str = Form(""), owner_name: str = Form(""),
    role: str = Form(""), contact_email: str = Form(""), resume_url: str = Form(""),
    github_url: str = Form(""), linkedin_url: str = Form(""), csrf_token: str = Form(...),
    profile_image: UploadFile | None = File(None),
    remove_profile_image: str | None = Form(None),
    _admin: dict = Depends(require_admin),
):
    validate_csrf_token(request, csrf_token)
    current_settings = load_settings()
    profile_image_url = current_settings.get("profile_image_url", "")
    if remove_profile_image == "on":
        profile_image_url = ""
    if profile_image and profile_image.filename:
        profile_image_url = _save_uploaded_image(profile_image, "profile")
    save_settings({"site_name": site_name, "owner_name": owner_name, "role": role,
                   "contact_email": contact_email, "resume_url": resume_url,
                   "github_url": github_url, "linkedin_url": linkedin_url,
                   "profile_image_url": profile_image_url})
    return RedirectResponse(url="/admin_dashboard", status_code=303)


@router.get("/health")
def health():
    try:
        from .services import check_database
        check_database()
    except Exception:
        return JSONResponse(
            {"status": "error", "database": "unavailable"},
            status_code=503,
        )

    return {"status": "ok", "database": "ok"}
