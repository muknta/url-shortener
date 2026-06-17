import json
import uuid

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.metrics.models import ClickEvent, EnrichmentStatus
from apps.urlapp.models import ShortLink


class ShortLinkModelTests(TestCase):
    def test_uuid7_primary_key(self):
        link = ShortLink.objects.create(code="abc123", given_url="https://example.com")
        self.assertIsInstance(link.id, uuid.UUID)
        self.assertEqual(link.id.version, 7)

    def test_defaults(self):
        link = ShortLink.objects.create(code="abc124", given_url="https://example.com")
        self.assertEqual(link.visit_count, 0)
        self.assertIsNotNone(link.created_date)

    def test_created_date_stable_across_saves(self):
        link = ShortLink.objects.create(code="abc125", given_url="https://example.com")
        original = link.created_date
        link.visit_count = 5
        link.save()
        link.refresh_from_db()
        self.assertEqual(link.created_date, original)

    def test_str(self):
        link = ShortLink.objects.create(code="abc126", given_url="https://example.com")
        self.assertEqual(str(link), "https://example.com")

    def test_code_unique(self):
        ShortLink.objects.create(code="unique1", given_url="https://example.com")
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            ShortLink.objects.create(code="unique1", given_url="https://other.com")


class ApiShortenTests(TestCase):
    def _post(self, url):
        return self.client.post(
            reverse("urlapp:api-shorten"),
            data=json.dumps({"url": url}),
            content_type="application/json",
        )

    def test_shorten_returns_json_and_persists(self):
        resp = self._post("https://example.com")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("url", data)
        code = data["url"].rstrip("/").split("/")[-1]
        self.assertTrue(ShortLink.objects.filter(code=code).exists())

    def test_shorten_rejects_empty_url(self):
        resp = self._post("")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_shorten_rejects_javascript_scheme(self):
        resp = self._post("javascript:alert(1)")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_shorten_rejects_ftp_scheme(self):
        resp = self._post("ftp://example.com")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_shorten_rejects_data_url(self):
        resp = self._post("data:text/html,<h1>hi</h1>")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_anonymous_has_no_author_but_captures_metadata(self):
        self.client.post(
            reverse("urlapp:api-shorten"),
            data=json.dumps({"url": "https://example.com"}),
            content_type="application/json",
            HTTP_X_FORWARDED_FOR="9.9.9.9",
            HTTP_USER_AGENT="AnonBrowser/1.0",
        )
        link = ShortLink.objects.get(given_url="https://example.com")
        self.assertIsNone(link.author)
        self.assertEqual(link.ip_address, "9.9.9.9")
        self.assertEqual(link.user_agent, "AnonBrowser/1.0")
        self.assertEqual(link.enrichment_status, EnrichmentStatus.PENDING)

    def test_authenticated_sets_author_to_user(self):
        user = User.objects.create_user("bob", password="pw12345!")
        self.client.login(username="bob", password="pw12345!")
        self._post("https://example.com")
        link = ShortLink.objects.get(given_url="https://example.com")
        self.assertEqual(link.author, user)

    def test_shorten_captures_creation_metadata(self):
        self.client.post(
            reverse("urlapp:api-shorten"),
            data=json.dumps({"url": "https://example.com"}),
            content_type="application/json",
            HTTP_X_FORWARDED_FOR="1.2.3.4",
            HTTP_USER_AGENT="TestBrowser/2.0",
            HTTP_ACCEPT_LANGUAGE="fr-FR",
            HTTP_REFERER="https://search.example.com",
        )
        link = ShortLink.objects.get(given_url="https://example.com")
        self.assertEqual(link.ip_address, "1.2.3.4")
        self.assertEqual(link.user_agent, "TestBrowser/2.0")
        self.assertEqual(link.accept_language, "fr-FR")
        self.assertEqual(link.referrer, "https://search.example.com")


class ApiPublicUrlsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bob", password="pw12345!")

    def test_returns_only_anonymous_links(self):
        ShortLink.objects.create(code="anon01", given_url="https://a.com")
        ShortLink.objects.create(code="usr001", given_url="https://b.com", author=self.user)
        resp = self.client.get(reverse("urlapp:api-public-urls"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        codes = [row["short_url"].split("/")[-1] for row in data]
        self.assertIn("anon01", codes)
        self.assertNotIn("usr001", codes)

    def test_accessible_to_anonymous(self):
        resp = self.client.get(reverse("urlapp:api-public-urls"))
        self.assertEqual(resp.status_code, 200)

    def test_response_shape(self):
        ShortLink.objects.create(code="shp001", given_url="https://shape.com")
        resp = self.client.get(reverse("urlapp:api-public-urls"))
        row = resp.json()[0]
        self.assertIn("short_url", row)
        self.assertIn("given_url", row)
        self.assertIn("visit_count", row)
        self.assertIn("created_date", row)


class ApiMyUrlsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bob", password="pw12345!")

    def test_requires_authentication(self):
        resp = self.client.get(reverse("urlapp:api-my-urls"))
        self.assertEqual(resp.status_code, 401)

    def test_returns_only_own_links(self):
        other = User.objects.create_user("alice", password="pw12345!")
        ShortLink.objects.create(code="mine01", given_url="https://mine.com", author=self.user)
        ShortLink.objects.create(code="hers01", given_url="https://hers.com", author=other)
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.get(reverse("urlapp:api-my-urls"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        codes = [row["short_url"].split("/")[-1] for row in data]
        self.assertIn("mine01", codes)
        self.assertNotIn("hers01", codes)

    def test_excludes_anonymous_links(self):
        ShortLink.objects.create(code="mine02", given_url="https://mine2.com", author=self.user)
        ShortLink.objects.create(code="anon01", given_url="https://anon.com")
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.get(reverse("urlapp:api-my-urls"))
        codes = [row["short_url"].split("/")[-1] for row in resp.json()]
        self.assertIn("mine02", codes)
        self.assertNotIn("anon01", codes)


class RedirectTests(TestCase):
    def test_redirect_increments_visit_count(self):
        link = ShortLink.objects.create(code="zzz999", given_url="https://example.com")
        self.client.get(f"/{link.code}/")
        link.refresh_from_db()
        self.assertEqual(link.visit_count, 1)

    def test_redirect_unknown_slug_returns_404(self):
        resp = self.client.get("/notfound/")
        self.assertEqual(resp.status_code, 404)

    def test_redirect_resolves_by_code(self):
        link = ShortLink.objects.create(code="tst001", given_url="https://example.com")
        resp = self.client.get(f"/{link.code}/")
        self.assertRedirects(resp, "https://example.com", fetch_redirect_response=False)


class ClickCaptureTests(TestCase):
    def setUp(self):
        self.link = ShortLink.objects.create(code="clk001", given_url="https://example.com")

    def test_anonymous_click_creates_event_with_no_accessed_by(self):
        self.client.get(f"/{self.link.code}/")
        self.assertEqual(ClickEvent.objects.count(), 1)
        event = ClickEvent.objects.first()
        self.assertIsNone(event.accessed_by)

    def test_authenticated_click_sets_accessed_by_user(self):
        user = User.objects.create_user("bob", password="pw12345!")
        self.client.login(username="bob", password="pw12345!")
        self.client.get(f"/{self.link.code}/")
        event = ClickEvent.objects.first()
        self.assertEqual(event.accessed_by, user)

    def test_click_captures_metadata_from_request(self):
        self.client.get(
            f"/{self.link.code}/",
            HTTP_USER_AGENT="TestBrowser/1.0",
            HTTP_ACCEPT_LANGUAGE="en-US",
            HTTP_REFERER="https://referrer.example.com",
        )
        event = ClickEvent.objects.first()
        self.assertEqual(event.user_agent, "TestBrowser/1.0")
        self.assertEqual(event.accept_language, "en-US")
        self.assertEqual(event.referrer, "https://referrer.example.com")

    def test_click_defaults_enrichment_status_to_pending(self):
        self.client.get(f"/{self.link.code}/")
        event = ClickEvent.objects.first()
        self.assertEqual(event.enrichment_status, EnrichmentStatus.PENDING)

    def test_click_does_not_write_to_profile(self):
        user = User.objects.create_user("carol", password="pw12345!")
        profile = user.profile
        original_ip = profile.ip_address
        self.client.login(username="carol", password="pw12345!")
        self.client.get(f"/{self.link.code}/", HTTP_X_FORWARDED_FOR="1.2.3.4")
        profile.refresh_from_db()
        self.assertEqual(profile.ip_address, original_ip)
