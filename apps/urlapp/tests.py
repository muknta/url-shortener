from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.urlapp.models import Surl


class SurlModelTests(TestCase):
    def test_defaults(self):
        """Surl created with correct defaults."""
        s = Surl.objects.create(short_url="abc123", given_url="https://example.com")
        self.assertEqual(s.visit_count, 0)
        self.assertIsNotNone(s.created_date)

    def test_created_date_stable_across_saves(self):
        """created_date must not change on subsequent saves (guards bug B1)."""
        s = Surl.objects.create(short_url="abc124", given_url="https://example.com")
        original = s.created_date
        s.visit_count = 5
        s.save()
        s.refresh_from_db()
        self.assertEqual(s.created_date, original)

    def test_str(self):
        s = Surl.objects.create(short_url="abc125", given_url="https://example.com")
        self.assertEqual(str(s), "https://example.com")


class ShortenFlowTests(TestCase):
    def test_shorten_returns_json_and_persists(self):
        resp = self.client.post(reverse("urlapp:shorten-url"), {"url": "https://example.com"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("url", data)
        short = data["url"].rstrip("/").split("/")[-1]
        self.assertTrue(Surl.objects.filter(pk=short).exists())

    def test_shorten_rejects_empty_url(self):
        resp = self.client.post(reverse("urlapp:shorten-url"), {"url": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_shorten_rejects_invalid_scheme(self):
        resp = self.client.post(reverse("urlapp:shorten-url"), {"url": "javascript:alert(1)"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_shorten_rejects_ftp_scheme(self):
        resp = self.client.post(reverse("urlapp:shorten-url"), {"url": "ftp://example.com"})
        self.assertEqual(resp.status_code, 400)

    def test_anonymous_has_no_author(self):
        self.client.post(reverse("urlapp:shorten-url"), {"url": "https://example.com"})
        self.assertIsNone(Surl.objects.first().author)

    def test_authenticated_sets_author(self):
        User.objects.create_user("bob", password="pw12345!")
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("urlapp:shorten-url"), {"url": "https://example.com"})
        self.assertEqual(Surl.objects.first().author.username, "bob")

    def test_redirect_increments_visit_count(self):
        s = Surl.objects.create(short_url="zzz999", given_url="https://example.com")
        self.client.get(f"/{s.short_url}/")
        s.refresh_from_db()
        self.assertEqual(s.visit_count, 1)

    def test_redirect_unknown_slug_returns_404(self):
        resp = self.client.get("/notfound/")
        self.assertEqual(resp.status_code, 404)


class ListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bob", password="pw12345!")

    def test_nobodys_list_shows_only_anonymous(self):
        Surl.objects.create(short_url="anon01", given_url="https://a.com")
        Surl.objects.create(short_url="usr001", given_url="https://b.com", author=self.user)
        resp = self.client.get(reverse("urlapp:nobodys-surls"))
        self.assertEqual(resp.status_code, 200)
        slugs = [s.short_url for s in resp.context["surls"]]
        self.assertIn("anon01", slugs)
        self.assertNotIn("usr001", slugs)

    def test_user_list_requires_login(self):
        resp = self.client.get(reverse("urlapp:user-surls"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_user_list_shows_only_own_urls(self):
        other = User.objects.create_user("alice", password="pw12345!")
        Surl.objects.create(short_url="mine01", given_url="https://mine.com", author=self.user)
        Surl.objects.create(short_url="hers01", given_url="https://hers.com", author=other)
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.get(reverse("urlapp:user-surls"))
        slugs = [s.short_url for s in resp.context["surls"]]
        self.assertIn("mine01", slugs)
        self.assertNotIn("hers01", slugs)
