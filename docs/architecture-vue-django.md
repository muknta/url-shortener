# Architecture: Vue 3 + Django Integration

## Overview

The app uses a **same-origin, session-auth SPA** pattern: Django serves a thin HTML shell for the three interactive pages, Vite builds and bundles the Vue app, and Vue takes over the DOM from there. Login/register/password-reset stay fully server-rendered.

---

## 1. Page load — Django serves the shell

When a user visits `/`, `/nobodys-urls/`, or `/my-urls/`, all three routes point to a single Django view (`shell_view` in `apps/urlapp/urls.py`). It renders `apps/urlapp/templates/urlapp/app.html` — a minimal HTML page that:

- Loads Bootstrap 4 CSS (shared with the auth pages)
- Injects the compiled Vue bundle via `{% vite_asset 'src/main.js' %}`
- Provides `<div id="app"></div>` as the Vue mount point

Django renders no list data or form content at this stage — it is only a shell. The `@ensure_csrf_cookie` decorator on `shell_view` guarantees the `csrftoken` cookie is set before Vue makes any requests.

---

## 2. Vue boot — client takes over

Once the browser loads `main.js`, Vue initialises:

```
main.js  →  createApp(App).use(router).mount("#app")
```

`App.vue` contains only `<RouterView />` — a placeholder that renders whichever component the router selects. All visible UI from this point is produced by Vue, not Django templates.

---

## 3. Routing — vue-router, not Django

`frontend/src/router.js` maps paths to components entirely client-side (history mode):

| Path | Component | Notes |
|---|---|---|
| `/` | `ShortenForm` | Shorten form + result display |
| `/nobodys-urls/` | `UrlList` (`mode="public"`) | Anonymous-created links |
| `/my-urls/` | `UrlList` (`mode="mine"`) | Authenticated user's links |

Django serves the same shell for all three paths, so a hard refresh or deep-link always works — Django returns the shell, Vue boots, and the router renders the right component based on `window.location.pathname`.

The navbar links in `app.html` are plain `<a>` tags, so they trigger a full page reload (Django → shell → Vue re-boot). A `<RouterLink>` inside a Vue component would do a client-side swap with no reload.

---

## 4. API calls — CSRF and session auth

`frontend/src/api.js` is the single fetch wrapper. All requests are same-origin, so no CORS is involved.

**Session cookie** — `credentials: 'same-origin'` tells the browser to attach the Django session cookie automatically on every request.

**CSRF token** — Django requires the `X-CSRFToken` header on all state-changing requests (POST). `getCsrfToken()` reads the `csrftoken` cookie (set by `@ensure_csrf_cookie`) from `document.cookie` and injects it into every request header. `CSRF_COOKIE_HTTPONLY` must remain `False` (the default) for this to work.

Exported API functions:

| Function | Method | Endpoint | Auth |
|---|---|---|---|
| `shortenUrl(url)` | POST | `/api/shorten/` | Optional (attaches author if logged in) |
| `fetchPublicUrls()` | GET | `/api/urls/public/` | None |
| `fetchMyUrls()` | GET | `/api/urls/mine/` | Required — 401 if anonymous |

---

## 5. Django API views

`apps/urlapp/api.py` handles all three endpoints with plain `JsonResponse` — no DRF.

- **`POST /api/shorten/`** — parses JSON body, validates with `URLValidator(schemes=["http","https"])`, generates a random 6-char code, saves a `ShortLink` with `author=request.user` if authenticated or `author=None` if anonymous. Returns `{"url": "https://host/<code>"}`. Handles `IntegrityError` on code collision with a single retry.

- **`GET /api/urls/public/`** — returns links where `author=None`, ordered by `-visit_count, -created_date`.

- **`GET /api/urls/mine/`** — checks `request.user.is_authenticated` server-side (returns 401 if not), then returns only that user's links. Ownership is enforced here, never trusted from the client.

---

## 6. Vue components

**`ShortenForm.vue`**

User types a URL → clicks Shorten → `submit()` calls `shortenUrl()` → POST to `/api/shorten/` → Django validates and creates the link → response `{"url": "..."}` is displayed. A Copy button appears once a result exists.

**`UrlList.vue`**

Shared by both list views; behaviour controlled by the `mode` prop (`"public"` or `"mine"`). On mount (`onMounted`), it calls the appropriate fetch function and renders the JSON response as a table. `watch(() => props.mode, load)` re-fetches if vue-router changes the prop during client-side navigation.

---

## 7. Boundary between Django and Vue

```
Django owns                         Vue owns
─────────────────────────────────   ─────────────────────────────────
/login/, /register/                 <div id="app"> and everything in it
/profile/, /password-reset*         client-side navigation between the 3 routes
/<code>/  (the redirect)            API calls and DOM updates
/api/*    (JSON responses)
/admin/
serving the shell HTML template
```

The auth pages are entirely Django-rendered with crispy-forms. When `login_required` redirects an anonymous user away from `/my-urls/`, that is a full reload back into server-rendered territory — Vue is not involved.

---

## 8. Build and deployment

**Dev** — two processes: `python manage.py runserver` (:8000) and `npm run dev` in `frontend/` (Vite, :5173). The developer opens `:8000`; `django-vite` injects Vite's HMR client into the shell, giving hot-reload. Same origin throughout — no CORS, no proxy needed.

**Prod** — `npm run build` emits `frontend/dist/`. `collectstatic` picks it up (listed in `STATICFILES_DIRS`). WhiteNoise (`CompressedManifestStaticFilesStorage`) serves the hashed assets. `django-vite` reads the Vite manifest and emits the correct hashed `<script>` tag. No Node runs in production.
