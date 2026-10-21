# Deploying to Render

The repository includes `render.yaml`, which provisions a Python web service with a persistent disk at `/var/lib/myblog`. The disk is required because SQLite data must survive deployments.

## Deploy with a Blueprint

1. Sign in to [Render](https://dashboard.render.com/).
2. Choose **New → Blueprint**.
3. Connect the GitHub repository `emaodoh/personal-blog` and select the `main` branch.
4. Render reads `render.yaml`. Approve the service and the 1 GB persistent disk.
5. When prompted for secret environment variables, set:
   - `ADMIN_USERNAME`: the admin username you want to use.
   - `ADMIN_PASSWORD`: a strong password, not the old development password.
6. Apply the Blueprint and wait for the health check to pass at `/health`.
7. Open the generated `onrender.com` URL and log in.

The `starter` plan is specified because Render requires a paid instance type for persistent disks. Confirm the current price in Render before applying the Blueprint.

## Existing articles

On the first start, `scripts/seed_database.py` loads `data/seed_articles.json` only when the `articles` table is empty. Redeploys keep the existing disk data and skip seeding. To seed additional content later, update the fixture and run the script through a Render Shell after deleting or migrating the existing database.

## Environment variables

`render.yaml` sets non-secret production values automatically. The admin credentials use `sync: false`, so they are entered in the Render dashboard and are not stored in Git. Do not put real credentials in `render.yaml`.

## After deployment

- Confirm HTTPS is active on the generated URL.
- Confirm the custom 404 page and `/health` endpoint work.
- Confirm the admin login and article CRUD flow work.
- Copy backups off the Render disk regularly; a backup stored only on the same disk does not protect against disk loss.

## CLI/API deployment

Actual deployment requires a Render account, GitHub connection, and either dashboard access or a Render API token. No Render CLI or API credentials are present in this environment.
