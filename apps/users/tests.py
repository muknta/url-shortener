from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


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
