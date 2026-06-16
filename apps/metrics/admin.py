from django.contrib import admin

from .models import ClickEvent


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "short_link",
        "clicked_at",
        "enrichment_status",
        "country_code",
        "is_proxy",
        "is_hosting",
        "ip_address",
    ]
    list_filter = ["enrichment_status", "country_code", "is_proxy", "is_hosting"]
    search_fields = ["short_link__code", "ip_address"]
    readonly_fields = [f.name for f in ClickEvent._meta.get_fields() if hasattr(f, "name")]
    ordering = ["-clicked_at"]
