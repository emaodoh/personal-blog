import json


def load_article():
    with open("article.json", "r") as file:
        articles = json.load(file)
    
    return articles
    

def save_article(articles):
    with open("article.json", "w") as file:
        json.dump(articles, file, indent=3)


def get_article_by_id(article_id):
    articles = load_article()

    for article in articles:
        if article["id"] == article_id:
            return article

def edit_article(title, content, article_id):
    articles = load_article()

    for article in articles:
        if article["id"] == article_id:
            article["content"] = content
            article["title"] = title
            save_article(articles)