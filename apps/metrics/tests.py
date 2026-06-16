from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone as dj_tz

from apps.metrics.enrichment.base import EnrichmentResult
from apps.metrics.management.commands.enrich_visitor_metadata import Command as EnrichCommand
from apps.metrics.management.commands.purge_metrics import Command as PurgeCommand
from apps.metrics.models import ClickEvent, EnrichmentStatus
from apps.urlapp.models import ShortLink


def _make_link(code="tst001"):
    return ShortLink.objects.create(code=code, given_url="https://example.com")


def _make_click(link, ip="1.2.3.4", status=EnrichmentStatus.PENDING):
    return ClickEvent.objects.create(
        short_link=link,
        ip_address=ip,
        enrichment_status=status,
    )


class EnrichmentCommandTests(TestCase):
    def setUp(self):
        self.link = _make_link()

    def _run_enrich(self, provider_results=None):
        if provider_results is None:
            provider_results = {}
        cmd = EnrichCommand()
        stub_provider = type("StubProvider", (), {"enrich": lambda self, ips: provider_results})()
        with patch(
            "apps.metrics.management.commands.enrich_visitor_metadata._load_provider",
            return_value=stub_provider,
        ):
            from io import StringIO

            cmd.stdout = StringIO()
            cmd.stderr = StringIO()
            cmd.handle(batch_size=100)

    def test_pending_to_done_when_provider_returns_result(self):
        click = _make_click(self.link, ip="1.2.3.4")
        result = EnrichmentResult(
            country_code="US",
            region="California",
            city="San Francisco",
            timezone="America/Los_Angeles",
            isp="Test ISP",
            asn="AS12345",
            is_proxy=False,
            is_hosting=False,
            is_mobile=False,
        )
        self._run_enrich({"1.2.3.4": result})
        click.refresh_from_db()
        self.assertEqual(click.enrichment_status, EnrichmentStatus.DONE)
        self.assertEqual(click.country_code, "US")
        self.assertEqual(click.city, "San Francisco")
        self.assertIsNotNone(click.enriched_at)

    def test_pending_to_failed_when_provider_has_no_result(self):
        click = _make_click(self.link, ip="9.9.9.9")
        self._run_enrich({})
        click.refresh_from_db()
        self.assertEqual(click.enrichment_status, EnrichmentStatus.FAILED)

    def test_done_rows_not_reprocessed(self):
        click = _make_click(self.link, ip="1.2.3.4", status=EnrichmentStatus.DONE)
        self._run_enrich({})
        click.refresh_from_db()
        self.assertEqual(click.enrichment_status, EnrichmentStatus.DONE)

    def test_distinct_ip_dedupe(self):
        _make_click(self.link, ip="3.3.3.3")
        link2 = _make_link(code="tst002")
        _make_click(link2, ip="3.3.3.3")

        called_ips = []
        result = EnrichmentResult(country_code="DE")

        def fake_enrich(self_inner, ips):
            called_ips.extend(ips)
            return {"3.3.3.3": result}

        stub = type("StubProvider", (), {"enrich": fake_enrich})()
        cmd = EnrichCommand()
        from io import StringIO

        cmd.stdout = StringIO()
        cmd.stderr = StringIO()
        with patch(
            "apps.metrics.management.commands.enrich_visitor_metadata._load_provider",
            return_value=stub,
        ):
            cmd.handle(batch_size=100)

        self.assertEqual(called_ips.count("3.3.3.3"), 1)

    def test_command_is_idempotent(self):
        click = _make_click(self.link, ip="7.7.7.7")
        result = EnrichmentResult(country_code="FR")
        self._run_enrich({"7.7.7.7": result})
        click.refresh_from_db()
        first_enriched_at = click.enriched_at
        # Run again — the row is DONE, so it won't be reprocessed
        self._run_enrich({"7.7.7.7": result})
        click.refresh_from_db()
        self.assertEqual(click.enriched_at, first_enriched_at)

    def test_enriches_profile_pending_rows_too(self):
        user = User.objects.create_user("zara", password="pw12345!")
        profile = user.profile
        profile.ip_address = "8.8.8.8"
        profile.enrichment_status = EnrichmentStatus.PENDING
        profile.save(update_fields=["ip_address", "enrichment_status"])

        result = EnrichmentResult(country_code="GB")
        self._run_enrich({"8.8.8.8": result})
        profile.refresh_from_db()
        self.assertEqual(profile.enrichment_status, EnrichmentStatus.DONE)
        self.assertEqual(profile.country_code, "GB")


class PurgeCommandTests(TestCase):
    def _run_purge(self, retention_days=30):
        cmd = PurgeCommand()
        from io import StringIO

        cmd.stdout = StringIO()
        with patch("apps.metrics.management.commands.purge_metrics.settings") as mock_settings:
            mock_settings.METRICS_RETENTION_DAYS = retention_days
            cmd.handle()

    def test_purges_old_rows(self):
        link = _make_link("purge01")
        old_click = _make_click(link, ip="1.1.1.1")
        old_click.clicked_at = dj_tz.now() - timedelta(days=31)
        ClickEvent.objects.filter(pk=old_click.pk).update(clicked_at=old_click.clicked_at)

        self._run_purge(retention_days=30)
        self.assertFalse(ClickEvent.objects.filter(pk=old_click.pk).exists())

    def test_keeps_recent_rows(self):
        link = _make_link("purge02")
        new_click = _make_click(link, ip="2.2.2.2")

        self._run_purge(retention_days=30)
        self.assertTrue(ClickEvent.objects.filter(pk=new_click.pk).exists())
