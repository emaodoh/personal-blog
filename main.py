import json


def load_article():
    with open("article.json", "r") as file:
        articles = json.load(file)
    
    return articles
    

def save_article():
    with open("article.json", "w") as file:
        json.dump(article, file, indent=3)


def get_article(article_id):
    articles = load_article()

    for article in articles:
        if article["id"] == article_id:
            return article

