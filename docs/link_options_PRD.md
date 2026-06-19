# PRD: Link Visibility, Custom Codes & Link Management

A follow-up to `improvements_PRD.md`. These were listed there as out-of-scope/future
("custom/vanity short codes", "link deletion"); this PRD specs them properly.

The project ("UrlShortener") is a Django 5.2 / Python 3.12 URL shortener with a Vue 3
SPA frontend (see `architecture-vue-django.md`). Django serves a thin shell and JSON
APIs; Vue owns the three interactive pages.

This PRD covers four cohesive product changes that all touch the shorten flow, the
`ShortLink` model, and the two list pages:

1. **Public/private visibility** — every creator (anonymous or authenticated) gets an
   `is_public` toggle, **off (private) by default**.
2. **Rename "nobody's urls" → "public urls"** everywhere (route, nav, code names).
3. **Custom short codes** — optional user-chosen code, 3–20 letters/digits, validated.
4. **Link management in My Urls** — soft-delete (recoverable in DB, hidden from UI and
   redirects). Restore/edit are explicitly out of scope for now.

---

## Decisions Made

These were settled during design and drive the schema and migration:

- **Visibility toggle applies to everyone**, not just anonymous users. The Public list
  becomes "links where `is_public=True`" rather than "links with no author". Default is
  **private** (`is_public=False`).
- **Existing anonymous links stay public.** A data migration backfills `is_public=True`
  for all current `author IS NULL` rows so today's public list is preserved unchanged.
  Everything created after the migration defaults to private.
- **Soft-deleted codes are freed for reuse.** Uniqueness moves from a column-level
  `unique=True` to a **partial unique constraint** scoped to active rows. A deleted
  link keeps its row (and `deleted_at`), but its code can be claimed by a new link.
- **Anonymous private links are fire-and-forget.** An anonymous creator gets the short
  URL back at creation, but because anonymous users have no My Urls page, a private anon
  link is unmanageable afterward. This is intended and acceptable.

---

## Current State (baseline)

`apps/urlapp/models.py` — `ShortLink(VisitorMetadata)`:

```python
id           = UUIDField(primary_key=True, default=uuid7, editable=False)
code         = SlugField(max_length=20, unique=True, db_index=True)
given_url    = URLField(max_length=500, validators=[URLValidator(schemes=["http","https"])])
visit_count  = IntegerField(default=0)
created_date = DateTimeField(auto_now_add=True)
author       = ForeignKey(AUTH_USER_MODEL, related_name="links",
                          on_delete=SET_NULL, blank=True, null=True)
```

- **"Public" today = `author IS NULL`** (anonymous). Authenticated users' links are
  always private (visible only in My Urls).
- `apps/urlapp/api.py`: `api_shorten` (POST, random 6-char code), `api_public_urls`
  (`author=None`), `api_my_urls` (`author=user`).
- `apps/urlapp/views.py`: `redirect_to_long` — `get_object_or_404(ShortLink, code=code)`.
- `apps/urlapp/urls.py`: routes `index` (`/`), `nobodys-surls` (`/nobodys-urls/`),
  `user-surls` (`/my-urls/`), the three API paths, and the catch-all `<slug:code>/`.
- Frontend: `ShortenForm.vue` (URL input + Shorten + result), `UrlList.vue` (shared,
  `mode` = `public` | `mine`), `router.js`, `api.js`.

---

## 1. Data Model Changes

`apps/urlapp/models.py`:

```python
from django.db.models import Q

class ShortLink(VisitorMetadata):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    code = models.SlugField(max_length=20, db_index=True)          # unique=True removed
    given_url = models.URLField(
        max_length=500, validators=[URLValidator(schemes=["http", "https"])]
    )
    visit_count = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False, db_index=True)  # NEW
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)  # NEW
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="links",
        on_delete=models.SET_NULL, blank=True, null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code"],
                condition=Q(deleted_at__isnull=True),
                name="urlapp_shortlink_unique_active_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["-visit_count", "-created_date"],
                name="urlapp_shortlink_visit_c_idx",
            ),
        ]
```

Notes:

- **`unique=True` is removed** from `code` and replaced by the partial
  `UniqueConstraint`. Two *active* links can never share a code, but a code from a
  soft-deleted link can be reused. Partial (conditional) unique constraints are
  supported on both SQLite (local) and PostgreSQL (prod).
- `db_index=True` stays on `code` for fast redirect lookups.
- **No custom manager.** The default `objects` manager continues to return all rows
  (including deleted) so the admin and reuse-checks still see them. Active-only filtering
  is done explicitly with `deleted_at__isnull=True` at each query site — matching the
  existing inline-filter style in `api.py`. Define a module-level helper to avoid
  repetition:

  ```python
  # apps/urlapp/models.py
  ACTIVE = Q(deleted_at__isnull=True)
  ```

### Migrations

Two migrations, generated and reviewed separately (per CLAUDE.md, model changes are
flagged before generating):

1. **Schema migration** — adds `is_public` and `deleted_at`, alters `code` (drops
   `unique=True`), adds the `UniqueConstraint`. Reversible.
2. **Data migration** — backfills existing anonymous links to public:

   ```python
   def forward(apps, schema_editor):
       ShortLink = apps.get_model("urlapp", "ShortLink")
       ShortLink.objects.filter(author__isnull=True).update(is_public=True)

   def backward(apps, schema_editor):
       pass  # no-op: is_public column is dropped by reversing migration 1
   ```

Run order is migration 1 then 2. Both run cleanly on SQLite and Postgres.

---

## 2. Custom Short Codes

### Validation rules

A new validator in `apps/urlapp/` (e.g. `validators.py` or inline in `api.py`):

- **Format**: `^[A-Za-z0-9]{3,20}$` — English letters and digits only, length 3–20.
  Hyphens/underscores are intentionally disallowed.
- **Reserved words** (compared case-insensitively): `admin`, `register`, `profile`,
  `login`, `logout`, `api`. These are the only single-segment top-level paths that a
  custom code could shadow (the redirect route `<slug:code>/` is matched last, so an
  explicit route always wins and would make such a code unreachable). The multi-segment
  auth paths (`password-reset`, …) and the list paths (`public-urls`, `my-urls`) contain
  hyphens, so the format rule already excludes them.
- **Active uniqueness**: rejected if an *active* link already uses the code
  (`ShortLink.objects.filter(ACTIVE, code=code).exists()`). A code belonging only to a
  soft-deleted link is allowed.

### Random fallback

When no custom code is supplied, `_rand_code()` generates a 6-char code as today, but
its collision check is scoped to active links only:

```python
if not ShortLink.objects.filter(ACTIVE, code=code).exists():
    return code
```

### Error messages (returned as 400)

| Condition | Message |
|---|---|
| Bad format | `Custom code must be 3–20 letters or digits.` |
| Reserved word | `That code is reserved. Pick another.` |
| Already in use | `That code is already taken.` |

---

## 3. API Changes (`apps/urlapp/api.py`)

### `POST /api/shorten/`

Request body gains two optional fields:

```json
{ "url": "https://example.com", "code": "mylink", "is_public": false }
```

- `code` — optional. If present and non-empty, validate (format → reserved → active
  uniqueness) and use it; on any failure return the matching 400 above. If absent/empty,
  fall back to `_rand_code()`.
- `is_public` — optional bool, defaults to `false`. Stored on the link for **all**
  creators (anonymous and authenticated).
- `author` — unchanged (`request.user` if authenticated, else `None`).
- The `IntegrityError`-retry path only applies to the random-code branch; a custom code
  that loses a race returns the "already taken" 400 rather than silently re-rolling.

Response unchanged: `{"url": "https://host/<code>"}`.

### `GET /api/urls/public/`

```python
ShortLink.objects.filter(ACTIVE, is_public=True).order_by("-visit_count", "-created_date")
```

### `GET /api/urls/mine/`

```python
ShortLink.objects.filter(ACTIVE, author=request.user).order_by("-visit_count", "-created_date")
```

Each row now also returns `id` (UUID, needed for the delete call) and `is_public` (so
the table can show a status badge):

```json
{ "id": "...", "short_url": "...", "given_url": "...",
  "visit_count": 0, "created_date": "...", "is_public": false }
```

(The public-list payload does **not** need `id`/`is_public` — keep it as-is.)

### `POST /api/urls/<uuid:pk>/delete/` — NEW (soft-delete)

- Login required (anonymous → 401).
- Ownership enforced in the query, never trusted from the client:

  ```python
  updated = ShortLink.objects.filter(
      ACTIVE, pk=pk, author=request.user
  ).update(deleted_at=timezone.now())
  if not updated:
      return JsonResponse({"error": "Not found"}, status=404)
  return JsonResponse({"ok": True})
  ```

- Identified by **UUID `pk`**, not `code` — because codes are reusable after deletion, a
  code is no longer a stable identifier. This is why `id` is added to the My Urls payload.
- CSRF stays on (the Vue `api.js` wrapper already sends `X-CSRFToken`). No `@csrf_exempt`.

### Redirect (`apps/urlapp/views.py`)

```python
link = get_object_or_404(ShortLink, ACTIVE, code=code)
```

Deleted links now 404 instead of redirecting.

---

## 4. Rename "nobody's urls" → "public urls"

| Location | From | To |
|---|---|---|
| `apps/urlapp/urls.py` path | `nobodys-urls/` | `public-urls/` |
| `apps/urlapp/urls.py` name | `nobodys-surls` | `public-surls` |
| `app.html` nav link | `/nobodys-urls/` "Nobody's urls" | `/public-urls/` "Public urls" |
| `base.html` nav (legacy) | `{% url 'urlapp:nobodys-surls' %}` "Nobody's urls" | `public-surls` "Public urls" |
| `frontend/src/router.js` | `/nobodys-urls/` | `/public-urls/` |

**Backward compatibility**: add a permanent redirect so old bookmarks keep working:

```python
from django.views.generic import RedirectView
path("nobodys-urls/", RedirectView.as_view(url="/public-urls/", permanent=True)),
```

`base.html` appears to be a legacy template no longer rendered by the Vue shell
(`app.html` is the active shell). Update it for consistency but verify whether it is
still referenced before relying on it.

---

## 5. Frontend (Vue)

### `frontend/src/api.js`

```js
export function shortenUrl(url, { code = "", isPublic = false } = {}) {
  return apiFetch("/api/shorten/", {
    method: "POST",
    body: JSON.stringify({ url, code, is_public: isPublic }),
  });
}

export function deleteUrl(id) {
  return apiFetch(`/api/urls/${id}/delete/`, { method: "POST" });
}

export function fetchPublicUrls() { return apiFetch("/api/urls/public/"); }
export function fetchMyUrls()     { return apiFetch("/api/urls/mine/"); }
```

### `ShortenForm.vue`

Insert the new controls **between the URL input row and the result box** (as requested):

- **Custom code input** (optional): a text field, ideally with the `host/` shown as a
  static prefix so users see the resulting link shape. Inline validation message area
  reuses the existing `.error-msg` styling for 400 responses.
- **"Make public" toggle**: a checkbox bound to a `isPublic` ref, **default `false`**,
  labelled e.g. "Make public (listed on Public urls)". Shown to everyone.

`submit()` passes both:

```js
const data = await shortenUrl(inputUrl.value, { code: customCode.value, isPublic: isPublic.value });
```

Error handling stays the same (set `error.value` from the thrown message), so a taken or
invalid custom code shows inline without losing the form state.

### `UrlList.vue` (`mine` mode only)

- Add a **Status** column rendering a badge: `Public` / `Private` from `url.is_public`.
- Add a **Delete** action column with a confirm dialog; on confirm call `deleteUrl(url.id)`
  and remove the row from `urls` on success.
- `public` mode is unchanged — no status/delete columns, no `id` needed.

Gate the new columns on `props.mode === "mine"` so the single shared component still
serves both pages.

### `router.js`

```js
{ path: "/public-urls/", component: UrlList, props: { mode: "public" } },
```

---

## 6. Tests (`apps/urlapp/tests.py`)

Add/extend coverage — auth, ownership, and URL validation are first-class per CLAUDE.md.

**Model / constraint**
- Two active links cannot share a code (IntegrityError).
- A soft-deleted link's code can be reused by a new active link.

**Shorten — custom code**
- Valid custom code is stored and returned.
- Bad format / reserved word / already-taken active code each return 400 with the right
  message.
- Empty/omitted code falls back to a random code.

**Shorten — visibility**
- `is_public=true` stores a public link; default (omitted) is private.
- An authenticated user's public link appears in `/api/urls/public/`.

**Public list**
- Lists only `is_public=True` and active links; excludes private and deleted.

**Soft-delete**
- Owner can soft-delete their link (`deleted_at` set, 200).
- Non-owner / anonymous cannot (404 / 401); the link stays active.
- A soft-deleted link 404s on redirect and disappears from My Urls.

**Migration**
- Existing `author IS NULL` rows are `is_public=True` after the data migration
  (optional, via a migration test or a manual data check).

---

## 7. Execution Order

```
1. Model: add is_public + deleted_at, drop code unique=True, add partial UniqueConstraint
2. Generate + review schema migration, then data migration (backfill anon → public)
3. api.py: custom-code validation + reserved words; is_public in shorten;
   public/mine filters use ACTIVE; add id/is_public to mine payload; add delete endpoint
4. views.py: redirect filters ACTIVE (deleted → 404)
5. urls.py: rename route + name to public-urls/public-surls; add old-path redirect;
   add delete path
6. Frontend: api.js (shortenUrl args + deleteUrl); ShortenForm controls;
   UrlList status + delete (mine); router path
7. Templates: nav rename in app.html (and legacy base.html)
8. Tests for all of the above
9. ruff check . && ruff format . && python manage.py test (CI runs on Postgres)
```

---

## 8. Files Touched

| File | Change |
|---|---|
| `apps/urlapp/models.py` | `is_public`, `deleted_at`, partial unique constraint, `ACTIVE` helper |
| `apps/urlapp/migrations/000X_*.py` | schema migration |
| `apps/urlapp/migrations/000Y_*.py` | data migration (anon → public) |
| `apps/urlapp/api.py` | custom-code validation, `is_public`, active filters, mine payload fields, delete view |
| `apps/urlapp/views.py` | redirect filters active links |
| `apps/urlapp/urls.py` | rename route/name, old-path redirect, delete path |
| `apps/urlapp/validators.py` (new, optional) | code format + reserved-word validator |
| `apps/urlapp/templates/urlapp/app.html` | nav rename |
| `apps/urlapp/templates/urlapp/base.html` | nav rename (legacy) |
| `frontend/src/api.js` | `shortenUrl` args, `deleteUrl` |
| `frontend/src/components/ShortenForm.vue` | custom-code input + public toggle |
| `frontend/src/components/UrlList.vue` | status + delete (mine mode) |
| `frontend/src/router.js` | `/public-urls/` path |
| `apps/urlapp/tests.py` | new tests |

---

## 9. Security & Constraints (carried from CLAUDE.md)

- Custom codes are validated against a strict allowlist regex and a reserved-word list;
  no raw SQL, all queries via the ORM.
- Soft-delete and the delete endpoint enforce **ownership** in the query
  (`author=request.user`), not just authentication; an attacker cannot delete another
  user's link by guessing its id.
- CSRF stays on; the Vue fetch wrapper sends `X-CSRFToken`. No `@csrf_exempt`.
- URL validation (`URLValidator(schemes=["http","https"])`) is unchanged — `javascript:`
  / `data:` schemes remain rejected.
- The production security block in `config/settings.py` is untouched.
- No new third-party dependencies.

---

## Out of Scope / Future

- Restoring (un-deleting) links and editing the destination URL or visibility after
  creation.
- Hard-delete / purge of soft-deleted rows (a future management command).
- Letting anonymous creators manage their links (would require claim tokens or accounts).
- QR codes, expiry, click analytics dashboards (already deferred in `improvements_PRD.md`).
</content>
</invoke>
