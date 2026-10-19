from fastapi import APIRouter, HTTPException

from .services import get_article_by_id, edit_article, delete_article, load_article, add_article



router = APIRouter()


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

def edit_article_api(article_id: int, title: str, content: str):
    try:
        edit = edit_article(title, content, article_id)

        return {"message": "Article edited successfully."}

    except ValueError as e:

        raise HTTPException(status_code=404, detail=str(e))


@router.post("/articles")

def add_article_api(title: str, content:str, summary: str):

    if not title or not content or not summary:
        raise HTTPException(status_code= 400, detail="All fields are required.")

    add_article(content, title, summary)

    return {"message": "Article added successfully."}