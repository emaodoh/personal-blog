from  flask import Flask, render_template, request,flash, redirect, url_for
from services import get_article_by_id, edit_article, delete_article, load_article, add_article
import os

app = Flask(__name__)
app.secret_key = "223ewsdsdsdewewew"

@app.route("/")
def home():
    articles = load_article()
    return render_template("index.html", articles=articles)



@app.route("/article/<int:article_id>")
def blog(article_id):
    article = get_article_by_id(article_id)
    
    return render_template("blog.html", articles=article)

@app.route("/edit_blog/<int:article_id>", methods=["GET", "POST"])
def edit_blog(article_id):
    article = get_article_by_id(article_id)
    if request.method == "POST":
        print("done")
        title = request.form["title"]
        content = request.form["content"]
        
        edit_article(title, content, article_id)

        flash("article updated successfully", "success")
        return redirect(url_for("edit_blog",article_id=article_id))

    return render_template("edit.html", article=article)



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        
        

        admin_username = "admin"
        admin_password = "password"
    

        if username == admin_username:
            if password == admin_password:
                return redirect(url_for("admin_dashboard"))

        else:
            return "incorrect password or username."




    return render_template("login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    articles = load_article()
    return render_template("admin.html", articles=articles)



@app.route("/delete_blog/<int:article_id>")
def delete_blog(article_id):
    delete_article(article_id)

    return redirect(url_for('admin_dashboard'))


@app.route("/add_blog", methods=["GET", "POST"])

def add_blog():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        summary = request.form["summary"]
        add_article(content, title, summary)
        return redirect(url_for('admin_dashboard'))
        

    return render_template("add_blog.html")



if __name__ == "__main__":
    app.run(debug=True)



