from django.contrib import admin

from .models import ShortLink

_VISITOR_FIELDS = [
    "ip_address", "user_agent", "accept_language", "referrer",
    "country_code", "region", "city", "timezone", "isp", "asn",
    "is_proxy", "is_hosting", "is_mobile", "enrichment_status", "enriched_at",
]


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ["code", "given_url", "author", "visit_count", "created_date", "enrichment_status", "country_code", "ip_address"]
    list_filter = ["enrichment_status", "country_code", "is_proxy", "is_hosting"]
    search_fields = ["code", "given_url", "ip_address"]
    readonly_fields = ["id", "created_date", "enriched_at"] + _VISITOR_FIELDS
    fieldsets = [
        (None, {"fields": ["id", "code", "given_url", "author", "visit_count", "created_date"]}),
        ("Creation context", {"fields": _VISITOR_FIELDS, "classes": ["collapse"]}),
    ]
