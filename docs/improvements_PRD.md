# PRD: Technical Improvements & Production Deployment

A follow-up to `migration_PRD.md`. The project ("UrlShortener") is now a modern
Django 5.2 / Python 3.12 URL shortener running locally on SQLite. This PRD covers the
work needed to make it production-grade and deployable: a linter/formatter (ruff),
PostgreSQL + Docker for production, CI/CD via GitHub Actions, a real test suite, and a
comparison of easy-to-use managed hosting options (a domain is already owned).

## Project Summary

| Aspect | Current | Target |
|---|---|---|
| Linting/formatting | None | Ruff (lint + format) + pre-commit |
| Production database | None (SQLite only) | PostgreSQL via `DATABASE_URL`, SQLite stays the local default |
| Static files | `collectstatic` only | WhiteNoise-served, built into the image |
| WSGI server | `runserver` | Gunicorn |
| Containerization | None | Multi-stage `Dockerfile` + `docker-compose.yml` (prod parity) |
| CI/CD | None | GitHub Actions: ruff + tests + deploy check on every push/PR |
| Tests | Broken / no-op | Real tests for models, views, and the shorten/redirect flow |
| Deployment | None | Managed PaaS with managed Postgres (recommendation: Render) |

### Decisions Made

- **Database strategy**: `DATABASE_URL` drives the engine. When it is unset, the app
  falls back to SQLite — so local `runserver` keeps working with zero config, and
  production just sets one env var.
- **Hosting recommendation**: **Render** (managed Postgres, free TLS, deploy-on-push,
  the Dockerfile we build works as-is). Railway and Fly.io documented as alternatives;
  a VPS + Compose path documented as the cheapest/most-control fallback.
- **App hardening scope**: minimal and correctness-focused for this PRD — fix latent
  bugs, add input validation, use atomic counter increments. Custom short codes and
  click analytics are explicitly **out of scope / future** (see §7).

---

## Bugs Found (fix as part of this work)

These exist in the current codebase and should be fixed alongside the improvements.

### B1 — `creat_date` resets on every visit (data-correctness bug)

`apps/urlapp/models.py`:

```python
creat_date = models.DateTimeField(auto_now=True)
```

`auto_now=True` updates the field on **every** `save()`. Because
`redirect_to_long()` calls `surl.save()` on each visit, the "creation date" is
silently overwritten every time the short link is clicked. The public list orders by
`-creat_date`, so ordering is corrupted too.

Fix: use `auto_now_add=True` (set once, on creation). Also rename to `created_date`
for clarity (optional; requires a migration either way).

### B2 — Visit counter is read-modify-write (race condition)

`apps/urlapp/views.py`:

```python
surl.visit_count += 1
surl.save()
```

Concurrent clicks can lose increments, and `save()` rewrites every column (which is
what triggers B1). Fix with an atomic DB-side update:

```python
Surl.objects.filter(pk=short_url).update(visit_count=F('visit_count') + 1)
```

This is atomic, faster, and only touches `visit_count` (so it can't disturb
`created_date`).

### B3 — Existing tests are no-ops

`apps/urlapp/tests.py` constructs `Surl(...)` instances but never calls `.save()`,
uses `date.today` (the method object, not a value), and asserts on unsaved instances.
They pass without testing anything real. Replaced wholesale in §6.

---

## Phase 1 — Ruff (Lint + Format)

Add a single `pyproject.toml` at the repo root as the home for tool config.

### `pyproject.toml`

```toml
[project]
name = "url-shortener"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"
line-length = 100
extend-exclude = [".venv", "migrations", "staticfiles"]

[tool.ruff.lint]
select = [
    "E", "W",   # pycodestyle
    "F",        # pyflakes
    "I",        # isort
    "UP",       # pyupgrade
    "B",        # flake8-bugbear
    "DJ",       # flake8-django
    "C4",       # flake8-comprehensions
]
ignore = ["E501"]  # line length handled by the formatter

[tool.ruff.format]
quote-style = "double"
```

Notes:
- `migrations/` is excluded from linting (auto-generated, noisy).
- `DJ` catches Django-specific smells (e.g. `null=True` on string fields, missing
  `__str__`, etc.).
- One-time cleanup pass: `ruff check --fix .` then `ruff format .`.

### Pre-commit hook

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Install once with `pre-commit install`. Add `pre-commit` and `ruff` to a new
dev-requirements file (§ below).

### `requirements-dev.txt`

```
-r requirements.txt
ruff>=0.6
pre-commit>=3.8
pytest>=8.0
pytest-django>=4.9
coverage>=7.6
```

---

## Phase 2 — PostgreSQL + Static Files + WSGI

### 2.1 Add production dependencies

`requirements.txt`:

```diff
 Django>=5.2,<5.3
 django-crispy-forms>=2.4
 crispy-bootstrap4>=2024.1
 sqlparse>=0.5
 python-dotenv>=1.0
+dj-database-url>=2.2
+psycopg[binary]>=3.2
+whitenoise>=6.7
+gunicorn>=23.0
```

`psycopg[binary]` is psycopg 3 (the modern driver) and needs no system build
dependencies in the image.

### 2.2 Database — `DATABASE_URL` with SQLite fallback

`config/settings.py`:

```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

- No `DATABASE_URL` set → SQLite (local dev unchanged).
- `DATABASE_URL=postgres://user:pass@host:5432/db` → Postgres, with connection
  pooling (`conn_max_age`) and health checks.

### 2.3 Static files — WhiteNoise

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # right after SecurityMiddleware
    ...
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

`CompressedManifestStaticFilesStorage` gives hashed, gzip/brotli-compressed,
far-future-cacheable assets — no nginx/CDN needed for an app this size.

### 2.4 Email — environment-driven SMTP (prod) / console (dev)

The migration left email on the console backend. Make it environment-driven so prod
can send real password-reset mail:

```python
if os.environ.get('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ['EMAIL_HOST']
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### 2.5 Proxy/HTTPS awareness

Behind a PaaS load balancer, Django needs to trust the forwarded protocol so
`SECURE_SSL_REDIRECT` doesn't loop and `request.scheme` is correct (it's used to build
the short URL in `shorten_url`):

```python
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # CSRF_TRUSTED_ORIGINS must include the real scheme+host in Django 4+
    CSRF_TRUSTED_ORIGINS = os.environ.get(
        'CSRF_TRUSTED_ORIGINS', 'https://yourdomain.com'
    ).split(',')
```

Add `CSRF_TRUSTED_ORIGINS` to the env var table.

---

## Phase 3 — Docker for Production

### 3.1 `Dockerfile` (multi-stage, non-root)

```dockerfile
# ---- build stage ----
FROM python:3.12-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home appuser
WORKDIR /app
COPY --from=build /install /usr/local
COPY . .
RUN python manage.py collectstatic --noinput
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
```

Notes:
- Two stages keep build tooling out of the final image (smaller, fewer CVEs).
- Runs as non-root `appuser`.
- `collectstatic` runs at build time so WhiteNoise serves a fully-populated tree.
- `SECRET_KEY` is supplied at build via a dummy value if needed; real secrets are
  injected at runtime as env vars (never baked into the image).
- Migrations are **not** run in `CMD` (avoids races with multiple workers/instances).
  Run them as a release/pre-deploy step (each platform's mechanism in §5).

### 3.2 `.dockerignore`

```
.venv/
.git/
db.sqlite3
staticfiles/
__pycache__/
*.pyc
.env
.pytest_cache/
docs/
*.md
```

### 3.3 `docker-compose.yml` (local production parity)

For running the prod stack locally (web + Postgres) to catch issues before deploying:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: urlshortener
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: urlshortener
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U urlshortener"]
      interval: 5s
      retries: 5

  web:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000"
    environment:
      SECRET_KEY: localdev-insecure-key
      DEBUG: "False"
      ALLOWED_HOSTS: localhost,127.0.0.1
      DATABASE_URL: postgres://urlshortener:localdev@db:5432/urlshortener
      CSRF_TRUSTED_ORIGINS: http://localhost:8000
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

`docker compose up --build` gives a production-like environment on `localhost:8000`.

---

## Phase 4 — Deployment Options Comparison

Goal: live on the owned domain with a **managed** Postgres and the least ongoing ops.
All three PaaS options consume the `Dockerfile` from Phase 3 unchanged.

| Option | Setup effort | Monthly cost (starter) | Managed Postgres | Backups | Custom domain + TLS | Notes |
|---|---|---|---|---|---|---|
| **Render** ⭐ | Lowest — `render.yaml` blueprint, deploy-on-push | Free web tier (spins down) → $7 web; DB on Supabase free tier | External (Supabase) | Supabase automatic | Few clicks, auto TLS | Best "it just works" story for Django+Docker; DB lives on Supabase |
| **Railway** | Very low — Dockerfile auto-detected, PG plugin | Usage-based, ~$5+ (after $5 trial credit) | Yes, plugin | Yes | Yes, auto TLS | Slickest dashboard/DX; cost scales with usage |
| **Fly.io** | Medium — `fly.toml`, `fly launch` | Cheap; generous allowance | Fly Postgres (you run it) or external | You configure | Yes, auto TLS | Global/edge, more control, slightly more ops |
| VPS + Compose | High — provision, nginx/caddy, certbot, backups | ~$4–6 (Hetzner/DO) | No — you run it | You configure (cron `pg_dump`) | Manual (caddy/certbot) | Cheapest + full control, but you own all ops |

### Recommendation: Render (web) + Supabase (database)

- The Phase-3 Dockerfile deploys as-is; no platform-specific server config.
- Supabase provides managed PostgreSQL with automatic backups and a generous free tier.
- Free TLS + simple custom-domain flow for the domain already owned.
- Deploy-on-push from GitHub pairs directly with the CI in Phase 5.
- Set `DATABASE_URL` to the Supabase Session mode pooler URI in the Render dashboard before the first deploy.

### `render.yaml` (Render blueprint)

```yaml
services:
  - type: web
    name: url-shortener
    runtime: docker
    plan: starter
    healthCheckPath: /
    preDeployCommand: python manage.py migrate
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: "False"
      - key: ALLOWED_HOSTS
        value: yourdomain.com
      - key: CSRF_TRUSTED_ORIGINS
        value: https://yourdomain.com
      - key: DATABASE_URL
        sync: false
```

`sync: false` means Render requires `DATABASE_URL` to be set manually in the dashboard
before the first deploy — paste the Supabase Session mode pooler URI there.
`preDeployCommand` runs migrations once per deploy — the safe place for them (not in
`CMD`). Set `EMAIL_*` env vars in the dashboard when wiring up real password-reset mail.

### Deploying to the owned domain

1. Create a Supabase project → **Settings → Database → Connection string** → copy the **Session mode pooler** URI (port 5432).
2. Create the Render service from `render.yaml` (or via dashboard pointing at the Dockerfile).
3. In Render **Environment**, set `DATABASE_URL` to the Supabase Session mode URI before the first deploy.
4. Add the custom domain in Render → it provisions a TLS cert automatically.
5. Point DNS: a `CNAME` (or `ALIAS`/`ANAME` at the apex) to the Render hostname.
6. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the real domain.
7. Run `python manage.py createsuperuser` via a Render one-off shell for admin access.

---

## Phase 5 — CI/CD (GitHub Actions)

`.github/workflows/ci.yml` — runs on every push and PR:

```yaml
name: CI
on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: ci
          POSTGRES_PASSWORD: ci
          POSTGRES_DB: ci
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U ci"
          --health-interval 5s --health-timeout 5s --health-retries 5
    env:
      SECRET_KEY: ci-secret-key
      DEBUG: "True"
      DATABASE_URL: postgres://ci:ci@localhost:5432/ci
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-dev.txt
      - name: Lint
        run: |
          ruff check .
          ruff format --check .
      - name: Test
        run: python manage.py test
      - name: Deploy check
        run: python manage.py check --deploy
        env:
          DEBUG: "False"
          ALLOWED_HOSTS: example.com
```

- Tests run against a real Postgres service container (catches Postgres-only issues).
- `check --deploy` runs with `DEBUG=False` so misconfigurations fail CI, not prod.

### Optional: deploy on merge to `master`

Render/Railway auto-deploy from GitHub natively (no workflow needed). If explicit
control is wanted, add a job gated on `github.ref == 'refs/heads/master'` that calls the
platform's deploy hook (`curl "$RENDER_DEPLOY_HOOK"`) using a repo secret. **Off by
default** — enable once CI is trusted.

---

## Phase 6 — Real Test Suite

Replace the broken `apps/urlapp/tests.py` with tests that exercise the DB and views.

```python
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from apps.urlapp.models import Surl


class SurlModelTests(TestCase):
    def test_defaults(self):
        s = Surl.objects.create(short_url="abc123", given_url="https://example.com")
        self.assertEqual(s.visit_count, 0)
        self.assertIsNotNone(s.created_date)

    def test_created_date_stable_across_saves(self):
        s = Surl.objects.create(short_url="abc124", given_url="https://example.com")
        original = s.created_date
        s.visit_count = 5
        s.save()
        s.refresh_from_db()
        self.assertEqual(s.created_date, original)  # guards bug B1


class ShortenFlowTests(TestCase):
    def test_shorten_returns_json_and_persists(self):
        resp = self.client.post(reverse("shorten_url"), {"url": "https://example.com"})
        self.assertEqual(resp.status_code, 200)
        short = resp.json()["url"].rstrip("/").split("/")[-1]
        self.assertTrue(Surl.objects.filter(pk=short).exists())

    def test_anonymous_has_no_author(self):
        self.client.post(reverse("shorten_url"), {"url": "https://example.com"})
        self.assertIsNone(Surl.objects.first().author)

    def test_authenticated_sets_author(self):
        User.objects.create_user("bob", password="pw12345!")
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("shorten_url"), {"url": "https://example.com"})
        self.assertEqual(Surl.objects.first().author.username, "bob")

    def test_redirect_increments_visit_count(self):
        s = Surl.objects.create(short_url="zzz999", given_url="https://example.com")
        self.client.get(f"/{s.short_url}")
        s.refresh_from_db()
        self.assertEqual(s.visit_count, 1)


class ListViewTests(TestCase):
    def test_nobodys_list_shows_only_anonymous(self):
        Surl.objects.create(short_url="anon01", given_url="https://a.com")
        u = User.objects.create_user("bob", password="pw12345!")
        Surl.objects.create(short_url="usr001", given_url="https://b.com", author=u)
        resp = self.client.get(reverse("nobodys-urls"))
        self.assertContains(resp, "anon01")
        self.assertNotContains(resp, "usr001")
```

Add a couple of `apps/users` tests (registration creates a user + profile via the
existing signal; login/logout redirects). Optionally run via `pytest-django` with
coverage; `manage.py test` works without extra config and is what CI uses.

---

## Phase 7 — App Hardening (Minimal, In Scope)

Correctness/safety only — no new features.

- **Input validation**: in `shorten_url`, reject empty/oversized input and restrict to
  `http`/`https` schemes (`URLValidator` with `schemes=['http', 'https']`). Prevents
  storing `javascript:` / `data:` URLs that would execute on redirect.
- **Atomic counter** (bug B2): `F('visit_count') + 1` update.
- **`created_date` fix** (bug B1): `auto_now_add=True`.
- **DB index** for the public-list ordering:
  ```python
  class Meta:
      indexes = [models.Index(fields=['-visit_count', '-created_date'])]
  ```
- **Optional, documented-only**: per-IP rate limiting on `shorten_url`
  (`django-ratelimit`) if abuse becomes a concern. Not installed by default.

### Out of Scope / Future (explicitly deferred)

- Custom/vanity short codes (user-chosen slugs + collision UX).
- Click analytics (timestamped click log, referrer, geo, dashboard).
- Link expiry / deletion / QR codes.
- API + tokens.

These are real product features deserving their own brainstorm + spec; bundling them
here would balloon scope. Listed so they're not forgotten.

---

## Execution Order

```
1. Ruff + pyproject.toml + pre-commit   → ruff check --fix . && ruff format .
2. Fix bugs B1–B3 (models, views, tests) + migration
3. Add prod deps + DATABASE_URL/WhiteNoise/gunicorn/email/proxy settings
4. Dockerfile + .dockerignore + docker-compose.yml
5. Verify locally: docker compose up --build  (prod parity on Postgres)
6. GitHub Actions CI (ruff + tests + check --deploy on Postgres)
7. Deploy to Render: render.yaml, env vars, custom domain + DNS + TLS
8. Post-deploy: migrate (preDeployCommand), createsuperuser, smoke test
```

---

## New Files Summary

| File | Purpose |
|---|---|
| `pyproject.toml` | Ruff config (lint + format) |
| `.pre-commit-config.yaml` | Pre-commit ruff hooks |
| `requirements-dev.txt` | Dev/test/lint tooling |
| `Dockerfile` | Multi-stage production image |
| `.dockerignore` | Keep build context lean |
| `docker-compose.yml` | Local production parity (web + Postgres) |
| `.github/workflows/ci.yml` | CI: lint + test + deploy check |
| `render.yaml` | Render blueprint (recommended host) |

## Environment Variables (production)

| Variable | Example | Notes |
|---|---|---|
| `SECRET_KEY` | _(generated)_ | Strong random value; never commit |
| `DEBUG` | `False` | Must be False in prod |
| `ALLOWED_HOSTS` | `yourdomain.com` | Comma-separated |
| `CSRF_TRUSTED_ORIGINS` | `https://yourdomain.com` | Required in Django 4+ behind TLS |
| `DATABASE_URL` | `postgres://user:pass@host:5432/db` | Unset → SQLite (local) |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | `smtp.provider.com` / `587` / `True` | Enables SMTP; unset → console backend |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | — | SMTP credentials |
| `DEFAULT_FROM_EMAIL` | `noreply@yourdomain.com` | From address for password-reset mail |

---

## Verification Plan

- `ruff check .` and `ruff format --check .` — clean.
- `python manage.py test` — all tests pass (locally on SQLite and in CI on Postgres).
- `python manage.py check --deploy` with `DEBUG=False` — no critical warnings.
- `docker compose up --build` — app serves on `localhost:8000` against Postgres;
  shorten + redirect + lists work; static assets load via WhiteNoise.
- After Render deploy: domain resolves over HTTPS, password-reset email sends, admin
  reachable, short links create + redirect, `created_date` stays fixed across visits.
