from django.contrib import admin

from .models import Profile

_VISITOR_FIELDS = [
    "ip_address",
    "user_agent",
    "accept_language",
    "referrer",
    "country_code",
    "region",
    "city",
    "timezone",
    "isp",
    "asn",
    "is_proxy",
    "is_hosting",
    "is_mobile",
    "enrichment_status",
    "enriched_at",
]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "enrichment_status", "country_code", "ip_address", "enriched_at"]
    list_filter = ["enrichment_status", "country_code", "is_proxy", "is_hosting"]
    search_fields = ["user__username", "ip_address"]
    readonly_fields = ["enriched_at"] + _VISITOR_FIELDS
    fieldsets = [
        (None, {"fields": ["user"]}),
        ("Login-origin snapshot", {"fields": _VISITOR_FIELDS, "classes": ["collapse"]}),
    ]
