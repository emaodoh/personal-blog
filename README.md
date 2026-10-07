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

To keep things simple for now, you can use the filesystem to store the articles. Each article will be stored as a separate file in a directory. The file will contain the title, content, and date of publication of the article. You can use JSON or Markdown format to store the articles.
Backend

You can use any programming language to build the backend of the blog. You don't have to make it as an API for this project, we have other projects for that. You can have pages that render the HTML directly from the server and forms that submit data to the server.
Frontend

For the frontend, you can use HTML and CSS (no need for JavaScript for now). You can use any templating engine to render the articles on the frontend.
Authentication

You can implement basic authentication for the admin section. You can either use the standard HTTP basic authentication or simply hardcode the username and password in the code for now and create a simple login page that will create a session for the admin.

After completing this project, you will have practised templating, filesystem operations, basic authentication, form handling, and rendering HTML pages from the server. You can extend this project further by adding features like comments, categories, tags, search functionality, etc. Make sure to check the other backend projects that go into more advanced topics like databases, APIs, security best practices etc.



<!-- 

Every journey begins with a reason.

For me, programming started with curiosity. I wanted to understand how websites, applications, and the technology we use every day actually work. At first, I only saw the finished products, but I became fascinated by the process of creating them.

That curiosity led me to programming, and it completely changed the way I think about technology.

## The Beginning

Like many beginners, I started with Python because it is simple to learn yet powerful enough to build real applications.

In the beginning, even writing a small program felt like a huge accomplishment. I spent time learning variables, loops, functions, and conditionals. Some concepts were easy to understand, while others took days of practice before they finally made sense.

There were moments when I felt stuck, but every small victory gave me the motivation to keep going.

## Learning Beyond Tutorials

One of the biggest lessons I've learned is that watching tutorials alone is not enough.

Real learning begins when you start building projects.

Projects force you to think critically, solve problems independently, and apply what you've learned in practical situations. They expose gaps in your knowledge and push you to improve.

That's when programming becomes exciting.

## My First Real Project

One of my most rewarding experiences has been building an Expense Tracker using Flask.

It started as a simple idea, but as the project grew, I learned much more than I expected.

I discovered how to:

* Organize a project into multiple files.
* Build web pages with HTML and CSS.
* Create routes using Flask.
* Store data using SQLite.
* Perform Create, Read, Update, and Delete (CRUD) operations.
* Debug errors and fix unexpected problems.
* Use Git and GitHub to track changes.

Building this project taught me that software engineering is not just about writing code. It's about designing solutions, organizing your work, and continuously improving your skills.

## The Challenges

Learning programming hasn't always been easy.

I've spent hours searching for bugs that turned out to be a missing colon, an incorrect file path, or a simple spelling mistake.

Sometimes an error message seemed impossible to understand.

Instead of becoming discouraged, I learned to treat every bug as an opportunity to learn something new.

Each problem solved made me a little more confident.

## Why I Continue to Learn

Technology is constantly evolving, and that's one of the reasons I enjoy this field.

There is always a new programming language, framework, or tool to explore.

Learning programming has also taught me patience, discipline, and persistence—qualities that are valuable far beyond software development.

Every project I build teaches me something new and prepares me for more complex challenges.

## Looking Toward Artificial Intelligence

While I enjoy web development, my long-term goal is to become an AI Engineer.

Artificial intelligence is changing the way people work, learn, and solve problems. I believe that building a strong foundation in software engineering will prepare me to create intelligent applications in the future.

I'm excited to continue learning about machine learning, data science, and AI while improving my software engineering skills.

## Final Thoughts

Programming is more than learning a language or memorizing syntax.

It is about solving problems, thinking logically, and creating something that can make a difference.

My journey is still in its early stages, and I know there is much more to learn.

Through this blog, I'll continue sharing my experiences, projects, lessons, and discoveries along the way.

Thank you for reading, and I hope my journey encourages you to start—or continue—your own. -->
