# CLAUDE.md

Guidance for working in this repository. Read this before making changes.

## Project overview

Django URL shortener with user accounts, public/private link lists, and
password reset via email.

- **Python 3.12 / Django 5.2 LTS**
- **SQLite** for local dev, **PostgreSQL** in production
- Bootstrap 4 + jQuery AJAX, django-crispy-forms + crispy-bootstrap4
- Apps live under `apps/` (`apps.urlapp`, `apps.users`); settings in `config/`

## Working agreement

### Confirm architecture before implementing

Do **not** start writing code for anything beyond a trivial, localized change
until the approach is agreed.

- For any new feature, schema change, dependency, or change that touches more
  than one module, **first describe the plan** (files affected, data model
  impact, migrations, trade-offs) and get explicit sign-off before editing.
- Surface architectural decisions explicitly: new third-party packages, changes
  to the URL/redirect model, auth flow changes, anything affecting the database
  schema, and anything that alters request/response or security boundaries.
- If a request is ambiguous or has more than one reasonable design, **ask
  first** — propose options with a recommendation rather than guessing.
- Prefer the smallest change that solves the problem. Match the conventions
  already in the surrounding code; don't introduce new patterns unprompted.
- Database migrations are not reversible casually — flag any model change and
  confirm the migration plan before generating it.

### Commits and code authorship

- **Do not mention any AI involvement anywhere.** No `Co-authored-by: Claude`,
  no "Generated with Claude Code", no "AI-assisted", and no similar trailers,
  attributions, or footers in commit messages, PR descriptions, or code
  comments.
- Write commit messages and comments as a human author would: describe the
  change and the reasoning, nothing about how it was produced.
- Only commit or push when explicitly asked.

## Security practices

This handles user accounts, passwords, and email — treat security as a
first-class concern.

- **Never commit secrets.** `SECRET_KEY`, DB credentials, and SMTP passwords
  come from environment variables / `.env` (gitignored). When adding config,
  read it via `os.environ` like the existing settings; keep `.env.example` in
  sync but with placeholder values only.
- **Never weaken the production security block** in `config/settings.py`
  (the `if not DEBUG:` section: `SECURE_SSL_REDIRECT`, HSTS, secure cookies,
  `X_FRAME_OPTIONS`, nosniff). If a change requires touching it, call it out
  explicitly and explain why.
- `DEBUG` must default safely and never be `True` in production. Don't add code
  paths that leak stack traces or settings.
- **Validate and sanitize all user input**, especially submitted URLs. Guard
  against open-redirect abuse, javascript:/data: schemes, and SSRF-style
  internal targets when handling shortened links.
- **Use the ORM and Django forms** for queries and validation — no raw SQL with
  string interpolation. Rely on Django's templating auto-escaping; never mark
  untrusted content `safe` or build HTML by hand.
- **Keep CSRF protection on.** AJAX requests must send the CSRF token. Do not
  add `@csrf_exempt`.
- **Enforce authorization, not just authentication.** Verify object ownership
  before showing or mutating a user's URLs; never trust an ID from the client.
- Use Django's auth, password hashing, and password validators
  (`AUTH_PASSWORD_VALIDATORS`) — don't roll custom crypto or auth.
- Be careful with email flows (password reset): don't leak whether an account
  exists, and keep tokens to Django's built-in mechanisms.
- Pin and review dependencies before adding them; prefer well-maintained
  packages and justify each new one.

## Development workflow

### Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then set a real SECRET_KEY
python manage.py migrate
```

### Lint and format (must pass before committing)

Ruff is the linter and formatter; config in `pyproject.toml`, enforced via
pre-commit and CI.

```bash
ruff check .
ruff format .
pre-commit run --all-files
```

### Tests

Tests run on PostgreSQL in CI. Run them locally before proposing a change is
done:

```bash
python manage.py test
# or, against the remote DB config:
TEST_REMOTE_DB=1 python manage.py test
```

- Write or update tests for any behavior change, especially auth, URL
  validation, and ownership checks.
- Don't claim something works until you've run the relevant command and seen it
  pass.

## Conventions

- Keep apps self-contained under `apps/<name>/`; new domain logic goes in the
  app it belongs to, not in `config/`.
- Follow existing import ordering and double-quote style (ruff `I` + format
  handle this).
- Don't commit `db.sqlite3`, `.env`, or anything in `staticfiles/`.
