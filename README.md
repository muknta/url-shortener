# url-shortener (UkrotitelSsylok)

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
| `DATABASE_URL` | _(not set — uses SQLite)_ | PostgreSQL connection string for production |
| `EMAIL_HOST` | _(not set)_ | SMTP host for production email |
| `EMAIL_PORT` | _(not set)_ | SMTP port (usually `587`) |
| `EMAIL_USE_TLS` | _(not set)_ | Set to `True` for TLS |
| `EMAIL_HOST_USER` | _(not set)_ | SMTP account username |
| `EMAIL_HOST_PASSWORD` | _(not set)_ | SMTP account password |

---

## Production Deployment

### Environment variables

```env
SECRET_KEY=<strong-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-smtp-password
```

### Switch to PostgreSQL

1. Add `psycopg2-binary` (or `psycopg2`) to `requirements.txt`
2. Update `DATABASES` in `settings.py` to read `DATABASE_URL` from the environment (use `dj-database-url` or parse manually)

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

### Static files

```bash
pip install whitenoise        # or serve via nginx/CDN
python manage.py collectstatic
```

Add `whitenoise.middleware.WhiteNoiseMiddleware` after `SecurityMiddleware` in `MIDDLEWARE`.

### WSGI server

```bash
pip install gunicorn
gunicorn url_shortener.wsgi
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
