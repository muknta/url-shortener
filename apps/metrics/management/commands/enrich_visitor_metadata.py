import importlib

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone as dj_tz

from apps.metrics.models import ClickEvent, EnrichmentStatus


def _load_provider():
    path = getattr(
        settings,
        "METRICS_GEO_PROVIDER",
        "apps.metrics.enrichment.ipapi.IpApiProvider",
    )
    module_path, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


class Command(BaseCommand):
    help = "Enrich pending ClickEvent and Profile rows with geo/proxy metadata via the configured provider"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=None,
            help="Max rows to process (default: METRICS_ENRICH_BATCH_SIZE setting or 100)",
        )

    def handle(self, *args, **options):
        from apps.users.models import Profile

        batch_size = options["batch_size"] or getattr(settings, "METRICS_ENRICH_BATCH_SIZE", 100)
        provider = _load_provider()

        pending_clicks = list(
            ClickEvent.objects.filter(enrichment_status=EnrichmentStatus.PENDING).order_by(
                "clicked_at"
            )[:batch_size]
        )
        pending_profiles = list(
            Profile.objects.filter(enrichment_status=EnrichmentStatus.PENDING).order_by(
                "origin_updated_at"
            )[:batch_size]
        )

        all_rows = pending_clicks + pending_profiles
        if not all_rows:
            self.stdout.write("No pending rows to enrich.")
            return

        distinct_ips = list({r.ip_address for r in all_rows if r.ip_address})
        self.stdout.write(f"Enriching {len(all_rows)} rows with {len(distinct_ips)} distinct IPs…")

        try:
            results = provider.enrich(distinct_ips)
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(f"Provider error: {exc}")
            results = {}

        now = dj_tz.now()
        done_ids = []
        failed_ids = []

        for row in all_rows:
            enrichment = results.get(row.ip_address) if row.ip_address else None
            if enrichment is not None:
                row.country_code = enrichment.country_code
                row.region = enrichment.region
                row.city = enrichment.city
                row.timezone = enrichment.timezone
                row.isp = enrichment.isp
                row.asn = enrichment.asn
                row.is_proxy = enrichment.is_proxy
                row.is_hosting = enrichment.is_hosting
                row.is_mobile = enrichment.is_mobile
                row.enrichment_status = EnrichmentStatus.DONE
                row.enriched_at = now
                done_ids.append(row.pk)
            else:
                row.enrichment_status = EnrichmentStatus.FAILED
                failed_ids.append(row.pk)

        update_fields = [
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

        for row in all_rows:
            row.save(update_fields=update_fields)

        self.stdout.write(f"Done: {len(done_ids)}, Failed: {len(failed_ids)}")
