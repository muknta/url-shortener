from .models import ClickEvent


def get_client_ip(request):
    """Return the client IP from X-Forwarded-For (first hop) or REMOTE_ADDR.

    Trustworthy only when running behind a known proxy such as Render, which sets XFF.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def extract_request_metadata(request):
    """Return a dict of VisitorMetadata fields captured silently from the request."""
    return {
        "ip_address": get_client_ip(request) or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "accept_language": request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
        "referrer": request.META.get("HTTP_REFERER", ""),
    }


def record_click(request, link):
    """Create a ClickEvent for a redirect. Keeps the view thin."""
    metadata = extract_request_metadata(request)
    accessed_by = request.user if request.user.is_authenticated else None
    ClickEvent.objects.create(short_link=link, accessed_by=accessed_by, **metadata)
