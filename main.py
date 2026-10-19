from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from services import get_article_by_id, edit_article, delete_article, load_article, add_article


app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="223ewsdsdsd09088lkkhgtre754323hty"
)


app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/home")
def home(request: Request):
    articles = load_article()
    return templates.TemplateResponse(request=request, name="index.html", context={"articles": articles})



@app.get("/article/{article_id}")
def blog(article_id: int, request: Request):
    article = get_article_by_id(article_id)
    
    return templates.TemplateResponse(request=request, name="blog.html", context= {"articles": article})



@app.get("/admin_dashboard")
def admin_dashboard(request: Request):
    articles = load_article()
    
    return templates.TemplateResponse(request=request, name="admin.html", context={"articles": articles})



@app.get("/delete_blog/{article_id}")
def delete_blog(request:Request, article_id: int):
    delete_article(article_id)

    flash(request, "Article deleted successfully!", "success")
    return RedirectResponse(url='/admin_dashboard', status_code=303)



@app.get("/edit_blog/{article_id}")
def edit_blog(article_id: int, request: Request):
    article = get_article_by_id(article_id)
    

    return templates.TemplateResponse(request=request, name="edit.html", context= {"article": article})



@app.post("/edit_blog/{article_id}")
def edit_blog(request: Request, article_id: int, title: str = Form(), content: str = Form()):

   
        
    edit_article(title, content, article_id)

    # flash("article updated successfully", "success")
    flash(request, "Article updated successfully!", "success")

    return RedirectResponse(url=f"/edit_blog/{article_id}",status_code=303)



@app.get("/login")
def login(request: Request):


    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
def login(request: Request, username: str = Form(), password: str = Form()):
    username = username.lower()
    
        
        

    admin_username = "admin"
    admin_password = "password"
    

    if username == admin_username:
        if password == admin_password:
            return RedirectResponse(url="/admin_dashboard", status_code=303)

    else:
        flash(request, "Incorrect Password", "success")
        
        return RedirectResponse(url="/login", status_code=303)



@app.get("/add_blog")

def add_blog(request: Request):

    return templates.TemplateResponse(request=request, name="add_blog.html")


@app.post("/add_blog")
def add_blog(request: Request, title: str = Form(),
             content: str = Form(),
             summary: str = Form(),
            ):
    add_article(content, title, summary)

    flash(request, "Blog added successfully!", "success")

    return RedirectResponse(url='admin_dashboard', status_code=303)
  

def flash(request, message, category="success"):
    request.session["flash"] = {
        "message": message,
        "category": category
    }