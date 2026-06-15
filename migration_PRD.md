# PRD: Migrate Django URL Shortener to Python 3.12

A 7-year-old Django 2.2 / Python 3.7 project ("UkrotitelSsylok") originally deployed on Heroku with PostgreSQL. The goal is to modernize it fully: run locally with Python 3.12, upgrade to Django 5.2 LTS, apply security best practices, and prepare for future deployment on a new domain/host.

## Project Summary

| Aspect | Current | Target |
|---|---|---|
| Python | 3.7 (Pipfile says 3.12 but deps are 3.7-era) | 3.12 |
| Django | 2.2 | 5.2 (latest LTS) |
| Database | PostgreSQL (Docker / Heroku) | SQLite for local dev |
| Deployment | Heroku (dead) + Docker Compose | Local `runserver`; future: new host |
| Secrets | Hardcoded in settings.py | Environment variables via `.env` |
| Package manager | Pipfile + requirements.txt | requirements.txt only |

### Decisions Made

- **Database**: SQLite for local dev. No existing data to preserve — fresh start.
- **Email**: Console backend for local dev (prints to terminal).
- **Heroku**: Completely dead — all Heroku/Docker artifacts will be removed.
- **Django version**: Direct jump 2.2 → 5.2 (codebase is ~200 lines, all breaking changes manageable in one pass).

---

## Phase 1 — Dependencies

### `url_shortener/requirements.txt`

Replace all ancient pinned dependencies with modern equivalents:

```diff
-certifi==2019.3.9
-chardet==3.0.4
-dataclasses==0.6
-dj-database-url==0.5.0
-Django==2.2
-django-crispy-forms==1.7.2
-django-heroku==0.3.1
-gunicorn==19.9.0
-idna==2.8
-psycopg2==2.8.2
-python-dateutil==1.5
-pytz==2019.1
-requests==2.21.0
-sqlparse==0.2.4
-urllib3==1.24.2
-martor
-gunicorn
+Django>=5.2,<5.3
+django-crispy-forms>=2.4
+crispy-bootstrap4>=2024.1
+sqlparse>=0.5
+python-dotenv>=1.0
```

**Removed packages and why:**

| Package | Reason |
|---|---|
| `django-heroku` | Abandoned, Heroku-only, breaks on modern Django |
| `gunicorn` | Production WSGI server, not needed for local dev |
| `psycopg2` | Using SQLite locally; not needed |
| `dj-database-url` | Heroku-only DATABASE_URL parsing |
| `dataclasses` | Built into Python 3.7+, the backport actually *breaks* on 3.12 |
| `certifi`, `chardet`, `idna`, `urllib3`, `requests` | Not used anywhere in the Django code |
| `python-dateutil` | Not imported anywhere |
| `pytz` | Django 5 uses `zoneinfo` (stdlib) |
| `martor` | Markdown editor, not used in any installed app or template |

**Added:**

| Package | Reason |
|---|---|
| `crispy-bootstrap4` | `django-crispy-forms` 2.x split template packs into separate packages |
| `python-dotenv` | Load secrets from `.env` file — replaces hardcoded credentials |

---

## Phase 2 — Settings & Security Overhaul

### `url_shortener/url_shortener/settings.py`

This is the biggest change — modernize settings and apply security best practices.

### 2.1 Remove `django_heroku`

```diff
-import django_heroku
+from dotenv import load_dotenv
+load_dotenv()
 ...
-django_heroku.settings(locals(), logging=not DEBUG, databases=not DEBUG)
```

### 2.2 Move `SECRET_KEY` to environment variable

The current key is committed to git — a critical security issue.

```diff
-SECRET_KEY = 'a6a6wt_&+e7zi_cygsdf=u!&21f#08u#%pp8^u+)$@v3=f6u6-'
+SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
```

A `.env` file will be created (and `.gitignore`'d) with a fresh random key for local dev.

### 2.3 Fix `DEBUG` setting

Currently the string `'False'`, which is *truthy* in Python!

```diff
-DEBUG = 'False'
+DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
```

### 2.4 Make `ALLOWED_HOSTS` configurable

```diff
-ALLOWED_HOSTS = ['theshortesturlontheinternet.herokuapp.com', 'localhost', '127.0.0.1', '0.0.0.0']
+ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
```

### 2.5 Switch database to SQLite

```diff
 DATABASES = {
     'default': {
-        'ENGINE': 'django.db.backends.postgresql_psycopg2',
-        'NAME': 'django_url_shortener',
-        'HOST': 'db-1',
-        'USER': 'heknt',
-        'PASSWORD': '1234',
-        'OPTIONS': {
-            'sslmode': 'disable',
-        },
+        'ENGINE': 'django.db.backends.sqlite3',
+        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
     }
 }
```

### 2.6 Add `DEFAULT_AUTO_FIELD`

Django 3.2+ warns without this.

```diff
+DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### 2.7 Switch email to console backend

```diff
-EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
-EMAIL_HOST = 'smtp.gmail.com'
-EMAIL_PORT = 587
-EMAIL_USE_TLS = True
-EMAIL_HOST_USER = 'hekntatest@gmail.com'
-EMAIL_HOST_PASSWORD = '***'
+EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### 2.8 Add `crispy-bootstrap4` template pack

crispy-forms 2.x requirement.

```diff
 CRISPY_TEMPLATE_PACK = 'bootstrap4'
+CRISPY_ALLOWED_TEMPLATE_PACKS = ('bootstrap4',)
```

### 2.9 Remove deprecated `USE_L10N`

Always `True` since Django 4.0.

```diff
-USE_L10N = True
```

### 2.10 Add security settings for future production

These are off in dev (`DEBUG=True`) but will activate automatically in production:

```python
# Security settings (active when DEBUG=False)
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'
```

---

## Phase 3 — Fix Breaking Code Changes

### 3.1 `urlapp/urls.py`

`django.conf.urls.handler404` / `handler500` were removed in Django 4.0. These imports aren't even used — just delete the import line:

```diff
 from django.urls import path
-from django.conf.urls import handler404, handler500
 from . import views
```

### 3.2 `url_shortener/urls.py`

The `LogoutView` with a positional `next_page` kwarg in `path()` is wrong — `next_page` should be set on the view, not as a third argument to `path()`:

```diff
-    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), {'next_page': settings.LOGOUT_REDIRECT_URL}, name='logout'),
+    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html', next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
```

### 3.3 `urlapp/models.py` — ✅ Already done by user

Dead utility functions (`f2`, `f`, `fd`) removed.

---

## Phase 4 — Cleanup

### Files to delete:

All Heroku and Docker artifacts are dead — remove everything:

| File | Reason |
|---|---|
| `Pipfile` | Pins Django==2.2 and has stale deps |
| `Pipfile.lock` | Stale lockfile |
| `Procfile` | Heroku-specific |
| `Dockerfile` | Based on Python 3.9.6, installs ancient requirements |
| `docker-compose.yml` | Hardcoded Postgres credentials, Heroku-oriented |
| `init-db.sh` | Docker Postgres init script |
| `test_connection.py` | Docker-specific Postgres connection test |
| `postgres_data2/` | Docker volume mount dir |
| `postgres_data3/` | Docker volume mount dir |
| `staticfiles/` | Heroku `collectstatic` output (auto-generated) |
| `.idea/` | JetBrains IDE config (shouldn't be in repo) |

### New files to create:

#### `.env` (gitignored)

```env
SECRET_KEY=<randomly-generated-50-char-key>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

#### `.env.example` (committed to git)

```env
SECRET_KEY=change-me-to-a-random-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

#### Update `.gitignore`

Add:
```
.env
db.sqlite3
.venv/
__pycache__/
staticfiles/
*.pyc
```

---

## Phase 5 — Fresh Migrations

No existing data — clean slate:

1. Delete all files in `urlapp/migrations/` (except `__init__.py`)
2. Delete all files in `users/migrations/` (except `__init__.py`)
3. Run `python3 manage.py makemigrations`
4. Run `python3 manage.py migrate`
5. Run `python3 manage.py createsuperuser` (optional, for admin access)

---

## Execution Steps Summary

```
1. Create venv          → python3 -m venv .venv && source .venv/bin/activate
2. Write requirements   → (updated requirements.txt)
3. Install deps         → pip install -r requirements.txt
4. Apply code fixes     → settings.py, urls.py
5. Create .env          → generate SECRET_KEY
6. Delete dead files    → Heroku/Docker/Pipfile artifacts
7. Reset migrations     → makemigrations + migrate
8. Run server           → python3 manage.py runserver
9. Verify               → open http://127.0.0.1:8000/
```

---

## Verification Plan

### Automated Tests
- `python3 manage.py check` — Django system check (catches common config errors)
- `python3 manage.py check --deploy` — security deployment checklist
- `python3 manage.py test` — Run existing test suite

### Manual Verification
- Open `http://127.0.0.1:8000/` — verify index page loads with the URL shortening form
- Submit a URL — verify AJAX shortening works and returns a short link
- Click the short link — verify redirect works
- Visit `/nobodys-urls/` — verify the public URL list loads
- Visit `/admin/` — verify Django admin loads
- Visit `/register/` — verify registration form renders
- Visit `/login/` — verify login form renders

---

## Future Deployment Notes

When moving to a new host/domain:

1. **Set environment variables** on the host (or use `.env`):
   - `SECRET_KEY` — generate a new random key
   - `DEBUG=False`
   - `ALLOWED_HOSTS=ridiculouslylong.link`
2. **Switch database** to PostgreSQL in production (update `DATABASES` + add `psycopg2-binary` to requirements)
3. **Switch email** to real SMTP backend (update `EMAIL_BACKEND` + configure SMTP credentials)
4. **Add `whitenoise`** for static file serving (or use nginx/CDN)
5. **Run `collectstatic`** before deploying
6. **Use a WSGI server** like `gunicorn` (add to requirements when deploying)
7. **Set up HTTPS** — the security settings in Phase 2.10 will enforce HSTS, secure cookies, and SSL redirect automatically when `DEBUG=False`
