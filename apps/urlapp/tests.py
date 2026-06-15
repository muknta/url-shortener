from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date
from apps.urlapp.models import Surl


class SurlTestCase(TestCase):
    def setUp(self):
        Surl(
            short_url = "ttt",
            given_url = "ttt",
            visit_count = 4,
            creat_date = date.today,
            author = User(),
        )
        Surl(
            short_url = "ttt",
            given_url = "ttt",
            creat_date = date.today,
            author = User(),
        )


    def test_surl(self):
        """Surls test"""
        s = Surl(
            short_url = "ttt",
            given_url = "ttt",
            visit_count = 4,
            creat_date = date.today,
            author = User(),
        )
        self.assertEqual(s.visit_count, 4)
        s = Surl(
            short_url = "ttt",
            given_url = "ttt",
            creat_date = date.today,
            author = User(),
        )
        self.assertEqual(s.visit_count, 0)
