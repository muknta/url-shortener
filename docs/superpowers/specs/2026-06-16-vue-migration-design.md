# Design: Migrate app UI from Bootstrap/jQuery/AJAX to Vue 3

**Date:** 2026-06-16
**Status:** Approved (design), pending spec review

## Goal

Replace the server-rendered + jQuery/AJAX front end of the URL shortener with a
Vue 3 single-page app for the interactive "app" pages, while keeping a single
Django server, a single deploy unit, and the existing Django session auth /
password-reset flows untouched. The repo root stays the full-stack root.

## Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Runtime architecture | Vue built by Vite, **served by Django** (one origin, one deploy). No standalone Node in production. |
| Folder layout | Keep Django at repo root unchanged; add a `frontend/` subfolder. Do **not** move backend into `backend/`. |
| UI scope | Vue owns the app pages (shorten form + public list + my list). Login/register/profile/password-reset stay Django server-rendered. |
| API layer | Plain Django `JsonResponse` views under `/api/`. No DRF. |
| App navigation | Single SPA with `vue-router` (history mode). |
| Auth | Django session auth unchanged. Same-origin; CSRF stays on; Vue sends `X-CSRFToken`. No tokens/JWT. |

## 1. Folder structure

```
url-shortener/                  ← repo root (full-stack from here)
├── manage.py                   ← Django stays at root
├── config/  apps/  requirements.txt  Dockerfile  render.yaml …
├── frontend/                   ← NEW: self-contained Vue/Vite project
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html              (Vite entry, dev only)
│   └── src/
│       ├── main.js             (create app, install router, mount)
│       ├── App.vue
│       ├── router.js
│       ├── api.js              (fetch wrapper: same-origin + CSRF header)
│       └── components/
│           ├── ShortenForm.vue
│           └── UrlList.vue     (shared by public + my-urls views)
└── frontend/dist/              ← build output (gitignored)
```

Rationale: meets the "same root, full-stack from here" requirement by adding
`frontend/` alongside the backend. Moving the backend into `backend/` would force
edits to `manage.py` paths, `Dockerfile`, `render.yaml`, `docker-compose.yml`, CI,
and every relative path — churn and risk with no functional gain. This is the
standard `django-vite` layout.

## 2. Dependencies

- **Python (prod):** add `django-vite` to `requirements.txt`. Nothing else.
- **JS (dev only, in `frontend/`):** `vue@^3`, `vue-router@^4`, `vite`. Managed by
  `npm`; never installed in the production Python image at runtime.

## 3. Runtime & dev workflow

- **Dev:** two processes — `python manage.py runserver` (:8000) and `npm run dev`
  (Vite, :5173). Developer always opens **:8000**; `django-vite` injects the Vite
  dev-server script tags into the Django-served shell, giving hot-reload. Page is
  served by Django → **same-origin** → session cookie + CSRF work with no CORS.
- **Prod:** `npm run build` → `frontend/dist/` → `collectstatic` (WhiteNoise
  `CompressedManifestStaticFilesStorage`, already configured) serves the hashed
  assets. `django-vite` switches automatically from dev mode to reading the Vite
  manifest. No Node runs in production.

## 4. Routing split

| Route | Owner | Notes |
|---|---|---|
| `/`, `/nobodys-urls/`, `/my-urls/` | **Vue** via vue-router | Django serves one shell template at each of these explicit paths; vue-router (history mode) renders the right view client-side. |
| `/login/`, `/register/`, `/profile/`, `/password-reset*` | **Django** | Unchanged server-rendered crispy-forms pages. |
| `/<short_url>/` | **Django** | The redirect. Stays the **last** URL pattern so explicit routes win — unchanged behavior. |
| `/admin/`, `/api/*` | **Django** | |

Because the three SPA paths are explicit Django routes returning the shell, a
refresh/deep-link on `/my-urls/` is served correctly, and the single-segment
short-url catch-all never conflicts (explicit patterns are matched first).

## 5. API layer — plain Django JSON views under `/api/`

New module `apps/urlapp/api.py` (or extend `views.py`), routed under `/api/`:

- `POST /api/shorten/` — refactor of the existing `shorten_url`. Same validation:
  `URLValidator(schemes=["http","https"])`, required field, IntegrityError retry
  on short-code collision. Attaches `author=request.user` when authenticated.
  Returns `{"url": "<scheme>://<host>/<code>"}`. **CSRF required.**
- `GET /api/urls/public/` — links with `author=None`, ordered
  `-visit_count, -created_date`. Returns a JSON list of
  `{short_url, given_url, visit_count, created_date}`.
- `GET /api/urls/mine/` — **auth required**. Returns only `request.user`'s links,
  same shape/order. Returns HTTP 401/403 when anonymous (ownership enforced
  server-side; never trust a client-supplied id).

All endpoints use the ORM + Django validators; no raw SQL; CSRF stays on; no
`@csrf_exempt`.

## 6. Auth & CSRF (security-critical)

- Session auth untouched. Vue's `api.js` calls with `credentials: 'same-origin'`.
- For POSTs, `api.js` reads the `csrftoken` cookie and sets the `X-CSRFToken`
  header (Django's standard AJAX-CSRF pattern). `CSRF_COOKIE_HTTPONLY` must remain
  default (False) so JS can read the cookie — verify current settings keep it so.
- `/my-urls/` shell and `/api/urls/mine/` both check
  `request.user.is_authenticated`.
- No new auth surface: no tokens, no JWT, no CORS.
- The production security block in `config/settings.py` (`SECURE_SSL_REDIRECT`,
  HSTS, secure cookies, `X_FRAME_OPTIONS`, nosniff) is **not weakened**.

## 7. Settings changes (`config/settings.py`)

- Add `"django_vite"` to `INSTALLED_APPS`.
- Add `DJANGO_VITE` config (dev server URL + manifest path under
  `frontend/dist/`).
- Add `frontend/dist/` to `STATICFILES_DIRS` so `collectstatic` picks up the
  build.
- Confirm CSRF cookie remains JS-readable (do not set `CSRF_COOKIE_HTTPONLY=True`).

## 8. Templates

- New thin shell template (e.g. `apps/urlapp/templates/urlapp/app.html`) that
  loads `{% vite_hmr_client %}` + `{% vite_asset 'src/main.js' %}` and contains
  the `<div id="app">` mount point. Keeps Bootstrap 4 CSS link for visual
  consistency with retained auth pages.
- Existing `index.html` / `surls.html` and the jQuery `main.js` AJAX are removed;
  the old `surls.html`-driven server rendering of lists is replaced by Vue + API.
- `base.html` retained/trimmed for the auth pages (still crispy-bootstrap4).

## 9. Styling

Keep **Bootstrap 4 CSS** (auth pages depend on crispy-bootstrap4). **Drop jQuery**
entirely from the app pages — Vue replaces all AJAX/DOM code. Old
`apps/urlapp/static/urlapp/*.js` AJAX deleted.

## 10. Testing & build tooling

- **Backend tests** (Django, on Postgres in CI): the 3 API endpoints — shorten
  validation (rejects empty / non-http(s) / `javascript:` etc.), `/api/urls/mine/`
  returns only the caller's links and 401/403 when anonymous, public list excludes
  authored links. Redirect + visit-count behavior unchanged.
- **CI:** add `npm ci && npm run build` before `collectstatic`; keep ruff + Django
  tests.
- **Dockerfile:** multi-stage — Node build stage produces `frontend/dist/`, copied
  into the Python stage before `collectstatic`.
- **.gitignore:** add `node_modules/` and `frontend/dist/`.

## Out of scope (YAGNI)

- DRF / serializers.
- Token/JWT auth, CORS.
- Rebuilding auth/password-reset in Vue.
- Moving the backend into a `backend/` directory.
- SSR / Nuxt.

## Verification plan

- `npm run dev` + `runserver`: home shorten form works (AJAX→`/api/shorten/`),
  short link redirects, public list + my-urls render from JSON, client-side nav
  between the three works, refresh on `/my-urls/` still loads.
- Anonymous user hitting `/my-urls/` data is denied.
- `npm run build` + `collectstatic` + `DEBUG=False`: assets served by WhiteNoise,
  app works without the Vite dev server.
- `ruff check .`, `python manage.py test` pass.
