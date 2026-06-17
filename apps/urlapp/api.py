import random
from string import ascii_letters, digits

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.metrics.services import extract_request_metadata

from .models import ShortLink


def _rand_code(n=6):
    alph = digits + ascii_letters
    while True:
        code = "".join(random.SystemRandom().choice(alph) for _ in range(n))
        if not ShortLink.objects.filter(code=code).exists():
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

    code = _rand_code()
    author = request.user if request.user.is_authenticated else None
    metadata = extract_request_metadata(request)

    link = ShortLink(code=code, given_url=url, author=author, **metadata)
    try:
        link.save()
    except IntegrityError:
        link.code = _rand_code()
        link.save()

    return JsonResponse({"url": f"{request.scheme}://{request.get_host()}/{link.code}"})


@require_GET
def api_public_urls(request):
    qs = (
        ShortLink.objects.filter(author=None)
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
        ShortLink.objects.filter(author=request.user)
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
