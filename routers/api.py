from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import require_admin_api
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
def delete_article_api(
    article_id: int,
    _admin: str = Depends(require_admin_api),
):
    try:
        delete_article(article_id)
        return { "message": "Article deleted successfully."}

    except ValueError as e:
        raise HTTPException(status_code= 404, detail=str(e))





@router.put("/articles/{article_id}")
def edit_article_api(
    article_id: int,
    article: BaseArticle,
    _admin: str = Depends(require_admin_api),
):
    try:
        return edit_article(
            article_id,
            article.title,
            article.content,
            article.summary,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))






@router.post("/articles")
def add_article_api(
    article: BaseArticle,
    _admin: str = Depends(require_admin_api),
):
    return add_article(article.title, article.content, article.summary)
