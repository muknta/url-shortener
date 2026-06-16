from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.metrics.models import EnrichmentStatus


class RegistrationTests(TestCase):
    def test_register_creates_user_and_profile(self):
        resp = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Testpass123!",
                "password2": "Testpass123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="newuser")
        self.assertTrue(hasattr(user, "profile"))

    def test_register_invalid_form_rerenders(self):
        resp = self.client.post(
            reverse("register"), {"username": "", "password1": "x", "password2": "y"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="").exists())


class AuthTests(TestCase):
    def setUp(self):
        User.objects.create_user("bob", password="pw12345!")

    def test_login_redirects_to_index(self):
        resp = self.client.post(reverse("login"), {"username": "bob", "password": "pw12345!"})
        self.assertRedirects(resp, reverse("urlapp:index"), fetch_redirect_response=False)

    def test_logout_redirects(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("urlapp:index"), fetch_redirect_response=False)


class ProfileSnapshotTests(TestCase):
    def test_first_login_populates_snapshot(self):
        user = User.objects.create_user("carol", password="pw12345!")
        profile = user.profile
        self.assertIsNone(profile.ip_address)

        self.client.post(
            reverse("login"),
            {"username": "carol", "password": "pw12345!"},
            HTTP_X_FORWARDED_FOR="10.0.0.1",
            HTTP_USER_AGENT="LoginBrowser/1.0",
        )
        profile.refresh_from_db()
        self.assertEqual(profile.ip_address, "10.0.0.1")
        self.assertEqual(profile.enrichment_status, EnrichmentStatus.PENDING)

    def test_login_from_new_ip_refreshes_snapshot(self):
        user = User.objects.create_user("dave", password="pw12345!")
        profile = user.profile
        profile.ip_address = "1.1.1.1"
        profile.save(update_fields=["ip_address"])

        self.client.post(
            reverse("login"),
            {"username": "dave", "password": "pw12345!"},
            HTTP_X_FORWARDED_FOR="2.2.2.2",
        )
        profile.refresh_from_db()
        self.assertEqual(profile.ip_address, "2.2.2.2")

    def test_login_from_same_ip_does_not_write(self):
        user = User.objects.create_user("eve", password="pw12345!")
        profile = user.profile
        profile.ip_address = "5.5.5.5"
        profile.enrichment_status = EnrichmentStatus.DONE
        profile.save(update_fields=["ip_address", "enrichment_status"])

        self.client.post(
            reverse("login"),
            {"username": "eve", "password": "pw12345!"},
            HTTP_X_FORWARDED_FOR="5.5.5.5",
        )
        profile.refresh_from_db()
        # Status should remain DONE — no re-enrichment triggered
        self.assertEqual(profile.enrichment_status, EnrichmentStatus.DONE)
