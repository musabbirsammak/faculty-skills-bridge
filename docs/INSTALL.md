# Installing Faculty Skills Bridge at your university

Each university runs its own copy, on its own domain, with its own data. This guide sets up a production installation with Docker: MySQL, the app, and Caddy for automatic HTTPS.

## What you need
- A Linux server with at least 2 GB of RAM and Docker (with Compose) installed
- A domain or subdomain pointing to the server, e.g. `skills.example.edu`
- Ports 80 and 443 open to the internet (Caddy uses them to get an HTTPS certificate)
- Optional: SMTP details so the app can send password-reset emails

## 1. Get the code and configure it
```bash
git clone <repository-url> faculty-skills-bridge
cd faculty-skills-bridge
cp .env.example .env
```

Edit `.env`:

| Setting | Value |
|---|---|
| `INSTITUTION_NAME` | Your university's name (you can change it later in the admin) |
| `DOMAIN` | e.g. `skills.example.edu` |
| `DJANGO_SECRET_KEY` | A long random string. Generate one with `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_ALLOWED_HOSTS` | Your domain, e.g. `skills.example.edu` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` + your domain |
| `DB_PASSWORD`, `DB_ROOT_PASSWORD` | Two different strong passwords |
| `EMAIL_*` | Your SMTP server, if you want password-reset emails |

## 2. Start it
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
The first start takes a few minutes. Database tables are created automatically.

## 3. Load the catalogue and create an administrator
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py seed_catalog
docker compose -f docker-compose.prod.yml exec web python manage.py seed_catalog --file catalog/data/seed_business.json
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 4. Set up your university in the admin
Open `https://your-domain/admin` and log in.

1. **Institution**: name, short name, logo URL, allowed email domains (e.g. `example.edu`), and whether new accounts need approval.
2. **Faculties**: add each faculty with its departments.
3. **Users**: once people have registered, set roles. *Head of department* and *Dean* need a department; a dean sees the faculty that department belongs to. *University leadership* is for the VC, pro-VC and similar roles.
4. **Courses**: adapt the catalogue to what your university teaches. Teachers can also add and edit courses from the app.

Then share the address with your teachers.

## Updating
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
Database changes are applied automatically when the app starts.

## Backups
```bash
docker compose -f docker-compose.prod.yml exec db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' > backup-$(date +%F).sql
```
Run this regularly (for example daily with cron) and keep copies off the server.

## Using your own web server instead of Caddy
If your university already runs nginx or another reverse proxy with HTTPS, remove the `caddy` service from `docker-compose.prod.yml`, add `ports: ["127.0.0.1:8000:8000"]` to the `web` service, and forward your domain to `http://127.0.0.1:8000`. Pass the `X-Forwarded-Proto` header so the app knows requests arrive over HTTPS.

## Privacy checklist before launch
- Tell teachers what leadership can see. The app's "What can others see?" page explains it; link to it in your announcement.
- Decide who has server and database access, and write it down. Server administrators can technically read the database.
- Keep `PRIVACY_MIN_GROUP` at 3 or higher.
