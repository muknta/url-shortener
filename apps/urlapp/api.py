import random
import re
from string import ascii_letters, digits

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.metrics.services import extract_request_metadata

from .models import ACTIVE, ShortLink

_CUSTOM_CODE_RE = re.compile(r"^[A-Za-z0-9]{3,20}$")
_RESERVED = frozenset(["admin", "register", "profile", "login", "logout", "api"])


def _validate_custom_code(code):
    if not _CUSTOM_CODE_RE.match(code):
        return "Custom code must be 3–20 letters or digits."
    if code.lower() in _RESERVED:
        return "That code is reserved. Pick another."
    if ShortLink.objects.filter(ACTIVE, code=code).exists():
        return "That code is already taken."
    return None


def _rand_code(n=6):
    alph = digits + ascii_letters
    while True:
        code = "".join(random.SystemRandom().choice(alph) for _ in range(n))
        if not ShortLink.objects.filter(ACTIVE, code=code).exists():
            return code


@require_POST
def api_shorten(request):
    import json

    try:
        body = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    url = body.get("url", "").strip()
    if not url:
        return JsonResponse({"error": "URL is required"}, status=400)

    validator = URLValidator(schemes=["http", "https"])
    try:
        validator(url)
    except ValidationError:
        return JsonResponse({"error": "Enter a valid http or https URL"}, status=400)

    custom_code = body.get("code", "").strip()
    is_public = bool(body.get("is_public", False))

    if custom_code:
        err = _validate_custom_code(custom_code)
        if err:
            return JsonResponse({"error": err}, status=400)
        code = custom_code
        use_random = False
    else:
        code = _rand_code()
        use_random = True

    author = request.user if request.user.is_authenticated else None
    metadata = extract_request_metadata(request)

    link = ShortLink(code=code, given_url=url, author=author, is_public=is_public, **metadata)
    try:
        link.save()
    except IntegrityError:
        if not use_random:
            return JsonResponse({"error": "That code is already taken."}, status=400)
        link.code = _rand_code()
        link.save()

    return JsonResponse({"url": f"{request.scheme}://{request.get_host()}/{link.code}"})


@require_GET
def api_public_urls(request):
    qs = (
        ShortLink.objects.filter(ACTIVE, is_public=True)
        .order_by("-visit_count", "-created_date")
        .values("code", "given_url", "visit_count", "created_date")
    )
    data = [
        {
            "short_url": f"{request.scheme}://{request.get_host()}/{row['code']}",
            "given_url": row["given_url"],
            "visit_count": row["visit_count"],
            "created_date": row["created_date"].isoformat(),
        }
        for row in qs
    ]
    return JsonResponse(data, safe=False)


@require_GET
def api_my_urls(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    qs = (
        ShortLink.objects.filter(ACTIVE, author=request.user)
        .order_by("-visit_count", "-created_date")
        .values("id", "code", "given_url", "visit_count", "created_date", "is_public")
    )
    data = [
        {
            "id": str(row["id"]),
            "short_url": f"{request.scheme}://{request.get_host()}/{row['code']}",
            "given_url": row["given_url"],
            "visit_count": row["visit_count"],
            "created_date": row["created_date"].isoformat(),
            "is_public": row["is_public"],
        }
        for row in qs
    ]
    return JsonResponse(data, safe=False)


@require_POST
def api_delete_url(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    updated = ShortLink.objects.filter(ACTIVE, pk=pk, author=request.user).update(
        deleted_at=timezone.now()
    )
    if not updated:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({"ok": True})
