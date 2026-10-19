from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from .services import get_article_by_id, edit_article, delete_article, load_article, add_article


templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.get("/")
def home(request: Request):
    articles = load_article()
    return templates.TemplateResponse(request=request, name="index.html", context={"articles": articles})



@router.get("/article/{article_id}")
def blog(article_id: int, request: Request):
    article = get_article_by_id(article_id)
    
    return templates.TemplateResponse(request=request, name="blog.html", context= {"articles": article})



@router.get("/admin_dashboard")
def admin_dashboard(request: Request):
    articles = load_article()
    
    return templates.TemplateResponse(request=request, name="admin.html", context={"articles": articles})



@router.get("/delete_blog/{article_id}")
def delete_blog(request:Request, article_id: int):
    delete_article(article_id)

    return RedirectResponse(url='/admin_dashboard', status_code=303)



@router.get("/edit_blog/{article_id}")
def edit_blog(article_id: int, request: Request):
    article = get_article_by_id(article_id)
    

    return templates.TemplateResponse(request=request, name="edit.html", context= {"article": article})



@router.post("/edit_blog/{article_id}")
def edit_blog(request: Request, article_id: int, title: str = Form(), content: str = Form()):

   
        
    edit_article(title, content, article_id)

    # flash("article updated successfully", "success")

    return RedirectResponse(url=f"/edit_blog/{article_id}",status_code=303)



@router.get("/login")
def login(request: Request):


    return templates.TemplateResponse(request=request, name="login.html")

@router.post("/login")
def login(request: Request, username: str = Form(), password: str = Form()):
    username = username.lower()
    
        
        

    admin_username = "admin"
    admin_password = "password"
    

    if username == admin_username:
        if password == admin_password:
            return RedirectResponse(url="/admin_dashboard", status_code=303)

    else:
        
        return RedirectResponse(url="/login", status_code=303)



@router.get("/add_blog")

def add_blog(request: Request):

    return templates.TemplateResponse(request=request, name="add_blog.html")


@router.post("/add_blog")
def add_blog(request: Request, title: str = Form(),
             content: str = Form(),
             summary: str = Form(),
            ):
    add_article(content, title, summary)


    return RedirectResponse(url='admin_dashboard', status_code=303)
  
