# Design: Click Metrics App + UUID7 Migration

**Date:** 2026-06-16
**Status:** Approved for planning
**Scope:** New `apps.metrics` app capturing per-click visitor metadata, a shared
abstract metadata model reused by `Profile`, asynchronous IP enrichment, and a
UUID7 PK migration that renames `Surl → ShortLink`.

> The project is **not yet deployed**, so destructive schema changes are
> acceptable and migrations may be reset rather than chained.

---

## 1. Goals

1. Record one row per click on a short link, with the visitor metadata available
   **silently** from the HTTP request.
2. Enrich each click with approximate geo + proxy/hosting flags **asynchronously**
   (off the redirect hot path), via a swappable third-party provider.
3. Define the visitor-metadata fields **once** and reuse them for both the metrics
   `ClickEvent` and a "last-seen" snapshot on `Profile`.
4. Move primary keys to **UUID7** (time-ordered) for the short-link model and the
   click model, and rename `Surl → ShortLink` while keeping the short code as the
   URL-facing field.

### Non-goals (explicitly out of scope)

- Browser Geolocation API (always requires a permission prompt — not "silent").
- A JS interstitial redirect page. The redirect stays an instant `302`.
- Viewport size capture (JS-only; not obtainable on a bare redirect).
- A real-time enrichment pipeline (Celery/Redis/worker). Enrichment is a scheduled
  batch job.
- An analytics dashboard / charts (future work; this spec only captures + stores).
- User-customizable/vanity short codes. The `code` column is widened to 20 chars now
  to accommodate them, but generation stays at 6 random chars; the custom-code UX
  (input, validation, reserved-word/collision handling) is a later TODO (see §13).

---

## 2. Key decisions (resolved during brainstorming)

| Decision | Choice |
|---|---|
| Location source | Server-side IP enrichment (no browser geolocation, no client JS) |
| Geo lookup timing | **Asynchronous**, via a scheduled batch job (redirect stays instant) |
| Provider | **ip-api.com** `/batch` endpoint (100 IPs/req, no key, free for non-commercial), behind a swappable interface |
| Timezone | Geo-derived (from enrichment), not the real browser timezone |
| Viewport | Dropped (JS-only) |
| Proxy/VPN/CDN | `is_proxy` + `is_hosting` flags from the provider (a lookup, so async) |
| `accessed_by` | Nullable FK to **`User`** (not `Profile`); set when the clicker has a valid session (resolved before the `302`). Avoids a `.profile` lookup on the hot path |
| Profile snapshot | Separate from clicks; updated on **login** via signal, only when the IP differs (§5.1) |
| Field reuse | Abstract `VisitorMetadata` base **in the metrics app**; `Profile` inherits it (`users → metrics`, acyclic; FKs are string refs) |
| UUID7 generation | `uuid6` pip package (`uuid7()` returns a stdlib `uuid.UUID` subclass) |
| Short-link model | Rename `Surl → ShortLink`; UUID7 `id` PK; `short_url → code` (unique slug in `/<code>/`) |
| Migration strategy | Reset `urlapp` migrations to a fresh `0001` (pre-deployment) |

---

## 3. Architecture overview

```
apps/metrics/                      (new app — owns the visitor-metadata concept)
  models.py
    VisitorMetadata     (abstract)  — shared field definitions
    ClickEvent(VisitorMetadata)     — one row per click; UUID7 PK
  enrichment/
    base.py             — GeoProvider interface + EnrichmentResult dataclass
    ipapi.py            — ip-api.com /batch implementation
    stub.py             — no-op provider (tests / disabled)
  management/commands/
    enrich_visitor_metadata.py      — scheduled batch enrichment
    purge_metrics.py                — PII retention cleanup
  admin.py, apps.py, tests.py, migrations/

apps/users/
  models.py
    Profile(VisitorMetadata)        — inherits the same fields as a last-seen snapshot

apps/urlapp/
  models.py
    ShortLink            (renamed from Surl; UUID7 PK; `code` slug)
  views.py, urls.py                 — redirect by `code`; write ClickEvent on click
```

**Dependency direction:** `users → metrics` (real import of the abstract base);
`metrics → urlapp` (ClickEvent → ShortLink) and `urlapp → users` (author → Profile)
via **string FK references only** (no module import). `ClickEvent.accessed_by` targets
`settings.AUTH_USER_MODEL`, so `metrics` no longer FKs into `apps.users` at all. The
only real Python import edge is `users → metrics`, which is acyclic. No `apps/common`
app is introduced.

---

## 4. Data model

### 4.1 `VisitorMetadata` (abstract, in `apps/metrics/models.py`)

Captured **immediately** at request time (server-side, no permission, no JS):

| Field | Type | Notes |
|---|---|---|
| `ip_address` | `GenericIPAddressField(null=True, blank=True)` | First hop of `X-Forwarded-For`, else `REMOTE_ADDR` |
| `user_agent` | `TextField(blank=True, default="")` | Raw `User-Agent`; parsed on display, not stored parsed |
| `accept_language` | `CharField(max_length=255, blank=True, default="")` | Raw `Accept-Language` header |
| `referrer` | `TextField(blank=True, default="")` | Raw `Referer` header |

Filled **later** by the enrichment job (all nullable/blank until then):

| Field | Type | ip-api source |
|---|---|---|
| `country_code` | `CharField(max_length=2, blank=True, default="")` | `countryCode` |
| `region` | `CharField(max_length=128, blank=True, default="")` | `regionName` |
| `city` | `CharField(max_length=128, blank=True, default="")` | `city` |
| `timezone` | `CharField(max_length=64, blank=True, default="")` | `timezone` (geo-derived) |
| `isp` | `CharField(max_length=255, blank=True, default="")` | `isp` / `org` |
| `asn` | `CharField(max_length=64, blank=True, default="")` | `as` |
| `is_proxy` | `BooleanField(null=True)` | `proxy` |
| `is_hosting` | `BooleanField(null=True)` | `hosting` (datacenter / CDN) |
| `is_mobile` | `BooleanField(null=True)` | `mobile` |
| `enrichment_status` | `CharField(choices=PENDING/DONE/FAILED, default=PENDING, db_index=True)` | drives the batch query |
| `enriched_at` | `DateTimeField(null=True, blank=True)` | set when enrichment completes |

```python
class Meta:
    abstract = True
```

### 4.2 `ClickEvent(VisitorMetadata)` (metrics)

| Field | Type | Notes |
|---|---|---|
| `id` | `UUIDField(primary_key=True, default=uuid7, editable=False)` | time-ordered |
| `clicked_at` | `DateTimeField(auto_now_add=True, db_index=True)` | "when clicked" |
| `short_link` | `FK("urlapp.ShortLink", on_delete=CASCADE, related_name="clicks")` | string ref |
| `accessed_by` | `FK(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL, related_name="clicks")` | set only for authenticated clickers. Points at **`User`** (not `Profile`) so the hot redirect path avoids the extra `.profile` lookup — `request.user` is already loaded by middleware |

```python
class Meta:
    ordering = ["-clicked_at"]
    indexes = [models.Index(fields=["short_link", "-clicked_at"])]
```

### 4.3 `Profile(VisitorMetadata)` (users)

The Profile snapshot is **independent of clicks**. It records the user's own
connection origin, captured **at login** (see §5.1), and is overwritten only when the
login IP differs from the stored one. Existing `user = OneToOneField(User, ...)` plus
the inherited `VisitorMetadata` fields and:

| Field | Type | Notes |
|---|---|---|
| `origin_updated_at` | `DateTimeField(null=True, blank=True)` | when the snapshot was last refreshed (renamed from the misleading "last_seen") |

The snapshot holds the **most recent login-origin** metadata (overwritten, not
history). It is enriched by the same batch job (it shares
`enrichment_status`/`enriched_at`). This is the reuse the original goal asked for:
the same `VisitorMetadata` field definitions serve both `ClickEvent` and `Profile`.

### 4.4 `ShortLink` (renamed from `Surl`, urlapp)

| Field | Type | Change |
|---|---|---|
| `id` | `UUIDField(primary_key=True, default=uuid7, editable=False)` | **new PK** |
| `code` | `SlugField(max_length=20, unique=True, db_index=True)` | renamed from `short_url`; the value in `/<code>/`. Width allows future user-chosen custom codes; generation stays at 6 random chars for now (see §13) |
| `given_url` | unchanged | |
| `visit_count` | unchanged | |
| `created_date` | unchanged (`auto_now_add=True`) | |
| `author` | `FK("users.Profile", null=True, blank=True, on_delete=SET_NULL, related_name="links")` | **changed** from `User` to `Profile` for consistency with `accessed_by`; `related_name` fixed from the `"user"` smell to `"links"`. String ref (`urlapp → users`, acyclic) |

`ShortLink` does **not** inherit `VisitorMetadata` — it is the link, not a visitor.

---

## 5. Capture flow (synchronous, on click)

In `urlapp.views.redirect_to_long(request, code)`:

1. `link = get_object_or_404(ShortLink, code=code)`.
2. Build the metadata dict from the request via a `metrics` helper
   `extract_request_metadata(request)` → `{ip_address, user_agent, accept_language, referrer}`.
   - IP via `get_client_ip(request)`: first hop of `X-Forwarded-For` if present
     (we run behind Render's proxy, which sets it), else `REMOTE_ADDR`. Document
     the trust assumption (XFF is only trustworthy behind a known proxy).
3. `accessed_by = request.user if request.user.is_authenticated else None`
   (no `.profile` lookup — `request.user` is already loaded).
4. `ClickEvent.objects.create(short_link=link, accessed_by=accessed_by, **metadata)`
   (defaults `enrichment_status=PENDING`).
5. Atomic counter (unchanged): `ShortLink.objects.filter(pk=link.pk).update(visit_count=F("visit_count") + 1)`.
6. `return redirect(link.given_url)`.

The click path does **not** touch `Profile` — the snapshot is a separate, login-driven
concern (§5.1).

Cost: one INSERT before the `302`. No `.profile` query, no network call on this path.
Enrichment is deferred entirely to the batch job.

> The capture (steps 2–4) should live in a small `metrics` service function
> (e.g. `record_click(request, link)`) so the view stays thin and the logic is
> unit-testable in isolation.

## 5.1 Profile snapshot (on login, IP-gated)

Independent of clicks. A `user_logged_in` signal receiver (in `apps/users/signals.py`)
refreshes the Profile's connection snapshot:

1. On `django.contrib.auth.signals.user_logged_in`, reuse
   `extract_request_metadata(request)` to read the current `{ip_address, user_agent,
   accept_language, referrer}`.
2. If the new `ip_address` **equals** the Profile's stored `ip_address`, do nothing
   (no write, no re-enrichment — repeat logins from the same network are cheap).
3. If it differs (or the snapshot is empty), copy the metadata onto the Profile, set
   `origin_updated_at=now()` and `enrichment_status=PENDING`, and `save()`. The batch
   job (§6) enriches it on its next run.

This fires even if the user never clicks a link, and at most once per login, only when
the network changed.

---

## 6. Asynchronous enrichment (scheduled batch job)

**Provider interface** (`apps/metrics/enrichment/base.py`):

```python
@dataclass
class EnrichmentResult:
    country_code: str = ""
    region: str = ""
    city: str = ""
    timezone: str = ""
    isp: str = ""
    asn: str = ""
    is_proxy: bool | None = None
    is_hosting: bool | None = None
    is_mobile: bool | None = None

class GeoProvider(Protocol):
    def enrich(self, ips: list[str]) -> dict[str, EnrichmentResult]: ...
```

**ip-api implementation** (`ipapi.py`):

- POST up to **100 IPs** per request to `http://ip-api.com/batch` with a `fields`
  query param selecting exactly the columns above (minimises payload).
- Free endpoint is **HTTP-only** (HTTPS needs a paid key). Server-to-server, no mixed
  content; the only data sent is IP addresses. Documented; a paid key + HTTPS base
  URL is a config swap later.
- Respect the rate limit (~15 batch requests/min). The job processes one batch per
  run by default; tune the schedule accordingly.
- Map results back to rows by IP. Provider/network failure → mark rows `FAILED`
  (re-pickable by a later run via a retry policy / manual reset), never crash the job.

**Management command** `enrich_visitor_metadata`:

1. Select `PENDING` rows across `ClickEvent` **and** `Profile` (ordered oldest-first),
   up to the batch size (default 100, settings-tunable).
2. Collect the **distinct** IPs (dedupe — many clicks share an IP).
3. Call `provider.enrich(distinct_ips)`.
4. Write enriched fields back to every row whose IP resolved; set
   `enrichment_status=DONE`, `enriched_at=now()`. Unresolved/failed → `FAILED`.
5. Idempotent and safe to re-run.

**Scheduling:** a Render **cron job** (or any cron) running the command every few
minutes. Enrichment lag = the schedule interval. No broker, no always-on worker, no
new runtime service.

> Optional future optimisation: an `IpGeoCache` table keyed by IP to avoid
> re-querying repeat IPs across runs. Out of scope here; in-batch dedupe is enough.

---

## 7. Settings (`config/settings.py`)

```python
METRICS_GEO_PROVIDER = "apps.metrics.enrichment.ipapi.IpApiProvider"  # import path
METRICS_GEO_BASE_URL = "http://ip-api.com/batch"
METRICS_ENRICH_BATCH_SIZE = 100
METRICS_RETENTION_DAYS = int(os.environ.get("METRICS_RETENTION_DAYS", "1000"))
```

The provider class is resolved by import path so tests can inject the stub provider
and a paid/alternate provider is a one-line change. No secrets required for ip-api
free; a future key would come from `os.environ` per the security rules.

---

## 8. Privacy & retention

IP address + geolocation is PII. Per the project's security posture:

- `purge_metrics` management command deletes `ClickEvent` rows older than
  `METRICS_RETENTION_DAYS` (and optionally nulls/anonymises IPs on retained rows).
  Run on the same cron mechanism as enrichment.
- No raw IPs are exposed in templates or to non-staff users; metrics are
  staff/admin-only for now.
- This data is captured silently and legitimately (server logs equivalent), but the
  retention command exists so it is not kept indefinitely.

---

## 9. URL / view / admin changes

- `urlapp/urls.py`: `path("<slug:code>/", views.redirect_to_long, name="redirect-to-long")`.
- `redirect_to_long(request, code)`: look up by `code`; call `record_click`.
- `shorten_url`: generate the random 6-char value into `code`; PK is auto-set by the
  UUID7 default. Collision retry (`rand_N_symb`) checks
  `ShortLink.objects.filter(code=...).exists()` instead of the PK. `author` is now set
  to `request.user.profile` (not `request.user`) when authenticated, else left null.
  Note the `on_delete` change `CASCADE → SET_NULL`: deleting a user no longer deletes
  their links (they become authorless); `accessed_by` is also `SET_NULL`.
- `UserSurlListView` (and any `author=`-filtered query) now filters by
  `author=self.request.user.profile` instead of `request.user`; the anonymous list
  (`author=None`) is unaffected.
- `metrics/admin.py`: register `ClickEvent` (read-mostly) with
  `list_display`/`list_filter` on `clicked_at`, `enrichment_status`, `country_code`,
  `is_proxy`, `is_hosting`; searchable by `code`/IP. Add the snapshot fields to the
  `Profile` admin if one exists.
- `config/settings.py` `INSTALLED_APPS`: add `apps.metrics` (listed before
  `apps.users` by convention, though abstract-base import works regardless of order).

---

## 10. Migrations

- **`urlapp`:** delete existing `0001`/`0002`, regenerate a fresh `0001_initial`
  reflecting `ShortLink` (UUID7 PK + `code` + `author → Profile`). Depends on `users`
  (Profile). Justified because the PK type change is destructive and the project is
  undeployed.
- **`metrics`:** new `0001_initial` for `ClickEvent`. Depends on `urlapp` (ShortLink)
  and `auth` (`accessed_by → User`) — not on `apps.users`. Acyclic.
- **`users`:** new migration adding the inherited `VisitorMetadata` fields +
  `origin_updated_at` to `Profile`. (Abstract inheritance copies fields, so this does
  not add a migration dependency on `metrics`.)
- Verify the full graph applies cleanly on a fresh DB (SQLite local + Postgres CI).

---

## 11. Dependencies

| Package | Why | Notes |
|---|---|---|
| `uuid6` | UUID7 generation | `uuid7()` returns a stdlib `uuid.UUID` subclass; drops into `UUIDField(default=uuid7)` |

The enrichment HTTP call uses the **stdlib** (`urllib.request` + `json`) — no
`requests`/`httpx` dependency added. Pin `uuid6` in `requirements.txt` and review
before adding.

---

## 12. Testing

- **ShortLink:** UUID7 PK is a valid version-7 UUID; `code` is unique; collision
  retry still works; redirect resolves by `code` and increments `visit_count`;
  `created_date` stable across saves (existing guarantee preserved).
- **Capture (click):** anonymous click → `ClickEvent` with `accessed_by is None`;
  authenticated click → `accessed_by == request.user` (the `User`, not a Profile).
  IP/UA/locale/referrer captured from the request; `enrichment_status` defaults to
  `PENDING`. The click does **not** write to `Profile`.
- **Profile snapshot (login):** first login (empty snapshot) → snapshot populated,
  `origin_updated_at` set, `enrichment_status=PENDING`; login from a **new IP** →
  snapshot refreshed; login from the **same IP** → no write (assert row unchanged, no
  re-enrichment).
- **Enrichment:** with a stub/mocked provider, `enrich_visitor_metadata` populates
  geo fields and flips `PENDING → DONE`; provider failure → `FAILED`; distinct-IP
  dedupe verified; command is idempotent.
- **Retention:** `purge_metrics` removes rows older than the cutoff and keeps newer
  ones.
- Tests run on SQLite locally and Postgres in CI (existing convention). UUID PKs and
  `GenericIPAddressField` behave on both.

---

## 13. Open considerations (flagged, not blocking)

- `author` (who *created* the link) and `accessed_by` (who *clicked* it while logged
  in) are **distinct roles** and intentionally target **different types**:
  `author → Profile` (set on the cold creation path, where a `.profile` lookup is
  cheap) and `accessed_by → User` (set on the hot redirect path, avoiding the extra
  lookup). The asymmetry is deliberate, not an oversight.
- ip-api free tier is non-commercial; if this ever monetises, a paid key (HTTPS +
  higher limits) is a settings swap.
- **Future TODO — custom/vanity codes:** the `code` column is 20 chars to support
  user-chosen slugs. Implementation deferred: needs a code-input form field,
  validation (charset/length, slug-safe), reserved-word handling (avoid clashing with
  routes like `shorten-url`, `my-urls`), collision UX, and an authorisation rule for
  who may set a custom code.
