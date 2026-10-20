from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .services import get_article_by_id, edit_article, delete_article, load_article, add_article



router = APIRouter()


class BaseArticle(BaseModel):
    title: str
    content: str
    summary: str


@router.get("/articles")
def get_article():
    articles = load_article()

    return articles


@router.get("/articles/{article_id}")

def get_article_by_id_api(article_id: int):
    try:
        article = get_article_by_id(article_id)
        return article

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.delete("/articles/{article_id}")

def delete_article_api(article_id: int):
    try:
        delete_article(article_id)
        return { "message": "Article deleted successfully."}

    except ValueError as e:
        raise HTTPException(status_code= 404, detail=str(e))





@router.put("/articles/{article_id}")

def edit_article_api(article: BaseArticle):
    try:
        edit = edit_article(article.title, article.content, article.article_id, article.summary)
        
        return edit

    except ValueError as e:

        raise HTTPException(status_code=404, detail=str(e))






@router.post("/articles")

def add_article_api(article: BaseArticle):

    article = add_article(article.content, article.title, article.summary)

    return article