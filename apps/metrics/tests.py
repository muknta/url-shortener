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


def _make_link(code="tst001", ip="1.2.3.4"):
    return ShortLink.objects.create(
        code=code,
        given_url="https://example.com",
        ip_address=ip,
        enrichment_status=EnrichmentStatus.PENDING,
    )


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

    def test_shortlink_pending_to_done(self):
        result = EnrichmentResult(country_code="US", city="New York")
        self._run_enrich({"1.2.3.4": result})
        self.link.refresh_from_db()
        self.assertEqual(self.link.enrichment_status, EnrichmentStatus.DONE)
        self.assertEqual(self.link.country_code, "US")
        self.assertIsNotNone(self.link.enriched_at)

    def test_shortlink_pending_to_failed_when_no_result(self):
        self._run_enrich({})
        self.link.refresh_from_db()
        self.assertEqual(self.link.enrichment_status, EnrichmentStatus.FAILED)

    def test_clickevent_pending_to_done(self):
        click = _make_click(self.link, ip="5.5.5.5")
        result = EnrichmentResult(country_code="DE", city="Berlin")
        self._run_enrich({"1.2.3.4": EnrichmentResult(), "5.5.5.5": result})
        click.refresh_from_db()
        self.assertEqual(click.enrichment_status, EnrichmentStatus.DONE)
        self.assertEqual(click.country_code, "DE")

    def test_done_rows_not_reprocessed(self):
        self.link.enrichment_status = EnrichmentStatus.DONE
        self.link.save(update_fields=["enrichment_status"])
        self._run_enrich({})
        self.link.refresh_from_db()
        self.assertEqual(self.link.enrichment_status, EnrichmentStatus.DONE)

    def test_distinct_ip_dedupe(self):
        _make_link(code="tst002", ip="1.2.3.4")

        called_ips = []
        result = EnrichmentResult(country_code="FR")

        def fake_enrich(self_inner, ips):
            called_ips.extend(ips)
            return {"1.2.3.4": result}

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

        self.assertEqual(called_ips.count("1.2.3.4"), 1)

    def test_command_is_idempotent(self):
        result = EnrichmentResult(country_code="GB")
        self._run_enrich({"1.2.3.4": result})
        self.link.refresh_from_db()
        first_enriched_at = self.link.enriched_at
        self._run_enrich({"1.2.3.4": result})
        self.link.refresh_from_db()
        self.assertEqual(self.link.enriched_at, first_enriched_at)

    def test_enriches_profile_pending_rows_too(self):
        user = User.objects.create_user("zara", password="pw12345!")
        profile = user.profile
        profile.ip_address = "8.8.8.8"
        profile.enrichment_status = EnrichmentStatus.PENDING
        profile.save(update_fields=["ip_address", "enrichment_status"])

        self._run_enrich({"1.2.3.4": EnrichmentResult(), "8.8.8.8": EnrichmentResult(country_code="JP")})
        profile.refresh_from_db()
        self.assertEqual(profile.enrichment_status, EnrichmentStatus.DONE)
        self.assertEqual(profile.country_code, "JP")


class PurgeCommandTests(TestCase):
    def _run_purge(self, retention_days=30):
        cmd = PurgeCommand()
        from io import StringIO

        cmd.stdout = StringIO()
        with patch("apps.metrics.management.commands.purge_metrics.settings") as mock_settings:
            mock_settings.METRICS_RETENTION_DAYS = retention_days
            cmd.handle()

    def test_purges_old_clickevent_rows(self):
        link = _make_link("purge01")
        old_click = _make_click(link, ip="1.1.1.1")
        ClickEvent.objects.filter(pk=old_click.pk).update(
            clicked_at=dj_tz.now() - timedelta(days=31)
        )
        self._run_purge(retention_days=30)
        self.assertFalse(ClickEvent.objects.filter(pk=old_click.pk).exists())

    def test_keeps_recent_clickevent_rows(self):
        link = _make_link("purge02")
        new_click = _make_click(link, ip="2.2.2.2")
        self._run_purge(retention_days=30)
        self.assertTrue(ClickEvent.objects.filter(pk=new_click.pk).exists())

    def test_nulls_ip_on_old_shortlink_but_keeps_row(self):
        link = _make_link("purge03", ip="3.3.3.3")
        ShortLink.objects.filter(pk=link.pk).update(
            created_date=dj_tz.now() - timedelta(days=31)
        )
        self._run_purge(retention_days=30)
        link.refresh_from_db()
        self.assertTrue(ShortLink.objects.filter(pk=link.pk).exists())
        self.assertIsNone(link.ip_address)

    def test_keeps_ip_on_recent_shortlink(self):
        link = _make_link("purge04", ip="4.4.4.4")
        self._run_purge(retention_days=30)
        link.refresh_from_db()
        self.assertEqual(link.ip_address, "4.4.4.4")
