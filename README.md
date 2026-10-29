Personal Blog

Build a personal blog to write and publish articles on various topics.

You are required to build a personal blog where you can write and publish articles. The blog will have two sections: a guest section and an admin section.

Guest Section — A list of pages that can be accessed by anyone:

    Home Page: This page will display the list of articles published on the blog.

    Article Page: This page will display the content of the article along with the date of publication.

Admin Section — are the pages that only you can access to publish, edit, or delete articles.

    Dashboard: This page will display the list of articles published on the blog along with the option to add a new article, edit an existing article, or delete an article.

    Add Article Page: This page will contain a form to add a new article. The form will have fields like title, content, and date of publication.

    Edit Article Page: This page will contain a form to edit an existing article. The form will have fields like title, content, and date of publication.

Here are the mockups to give you an idea of the different pages of the blog.

Pages that anyone can access
Personal Blog

Pages that only the admin can access
Personal Blog
How to Implement

Here are some guidelines to help you implement the personal blog:
Storage

Articles are stored in a local SQLite database. Set `DATABASE_PATH` in production and keep the database on persistent storage. The `articles` table contains each article's title, summary, and content, and the schema is initialized automatically when the application starts.
Backend

You can use any programming language to build the backend of the blog. You don't have to make it as an API for this project, we have other projects for that. You can have pages that render the HTML directly from the server and forms that submit data to the server.

Authentication

The admin account is stored in the local SQLite database with a salted password hash. Provide `ADMIN_USERNAME` and `ADMIN_PASSWORD` through environment variables; the account is created or updated at startup. Successful logins create an HTTP-only, SameSite=Lax session that is marked Secure when `SESSION_COOKIE_SECURE=true`. All admin pages and article write APIs require that session. Logging out invalidates it immediately.

Frontend

For the frontend, you can use HTML and CSS (no need for JavaScript for now). You can use any templating engine to render the articles on the frontend.

Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for persistent storage, HTTPS with Let's Encrypt, environment configuration, and database backups. Render deployment is covered in [RENDER.md](RENDER.md).

After completing this project, you will have practised templating, filesystem operations, basic authentication, form handling, and rendering HTML pages from the server. You can extend this project further by adding features like comments, categories, tags, search functionality, etc. Make sure to check the other backend projects that go into more advanced topics like databases, APIs, security best practices etc.

## Hybrid portfolio and blog

The public homepage introduces the portfolio owner, highlights published projects, shows recent published articles, and links to contact details. Projects and articles have separate public listings; existing article URLs at `/article/{id}` remain available.

The admin dashboard manages articles, projects, the Home/About/Contact page content, and site settings. Projects can be saved as drafts with only a title; descriptions, technologies, image URLs, and demo or repository URLs are optional. Existing articles are migrated as published so their public visibility and content are preserved.
