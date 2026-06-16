# url-shortener (UrlShortener)

A Django URL shortener with user accounts, public/private link lists, and password reset via email.

Features: register, login, restore password by email, shorten URLs via AJAX, view own and anonymous ("nobody's") URLs.

## Stack

- Python 3.12 / Django 5.2 LTS
- SQLite (local dev) / PostgreSQL (production)
- Bootstrap 4 + jQuery AJAX
- django-crispy-forms + crispy-bootstrap4

---

## Local Development

### 1. Clone and create the virtual environment

```bash
git clone <repo-url>
cd url-shortener
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the `.env` file

```bash
cp .env.example .env
```

Edit `.env` and set a real secret key:

```env
SECRET_KEY=<random-50-char-string>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Generate a key with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4. Run migrations

```bash
cd url_shortener
python manage.py migrate
```

### 5. (Optional) Create a superuser for admin access

```bash
python manage.py createsuperuser
```

### 6. Start the dev server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Environment Variables

All configuration is driven by `.env` (never committed to git).

| Variable | Dev default | Description |
|---|---|---|
| `SECRET_KEY` | _(required)_ | Django secret key — generate a fresh random value |
| `DEBUG` | `True` | Set to `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames |
| `DATABASE_URL` | `postgres://urlshortener:localdev@db:5432/urlshortener` | PostgreSQL connection string; unset falls back to SQLite |
| `TEST_REMOTE_DB` | `false` | Set to `true` to force Supabase `DATABASE_URL` (SSL required, no SQLite fallback) |
| `EMAIL_HOST` | _(not set)_ | SMTP host for production email |
| `EMAIL_PORT` | _(not set)_ | SMTP port (usually `587`) |
| `EMAIL_USE_TLS` | _(not set)_ | Set to `True` for TLS |
| `EMAIL_HOST_USER` | _(not set)_ | SMTP account username |
| `EMAIL_HOST_PASSWORD` | _(not set)_ | SMTP account password |

---

## Production Deployment

Architecture: **Render** (web service, Docker) + **Supabase** (managed PostgreSQL).

### 1. Set up the database on Supabase

1. Create a new project at [supabase.com](https://supabase.com).
2. Go to **Settings → Database → Connection string**.
3. Copy the **Session mode pooler** URI (port `5432`) — this works correctly with Django's persistent connections (`CONN_MAX_AGE`).
   Format: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
4. Keep this URI handy — you will set it as `DATABASE_URL` in Render.

### 2. Deploy to Render

1. Connect the GitHub repo in the Render dashboard and select **"Use render.yaml"**.
2. Before the first deploy, go to **Environment** and set `DATABASE_URL` to the Supabase Session mode URI.
3. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to your real domain.
4. Deploy — `preDeployCommand: python manage.py migrate` runs migrations automatically on each deploy.
5. Add a custom domain in Render → it provisions TLS automatically → point a `CNAME` (or `ALIAS`) in your DNS to the Render hostname.
6. Run `python manage.py createsuperuser` via a Render one-off shell for admin access.

### Environment variables

```env
SECRET_KEY=<strong-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-smtp-password
```

### Switch email to SMTP

In `settings.py`, replace the console backend block with:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
```

### Security settings

When `DEBUG=False`, the following are activated automatically (already in `settings.py`):

- `SECURE_SSL_REDIRECT` — redirects all HTTP to HTTPS
- `SECURE_HSTS_SECONDS = 31536000` — enforces HSTS for 1 year
- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` — cookies only over HTTPS
- `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_BROWSER_XSS_FILTER`
- `X_FRAME_OPTIONS = 'DENY'`

Run the deployment checklist before going live:

```bash
python manage.py check --deploy
```
