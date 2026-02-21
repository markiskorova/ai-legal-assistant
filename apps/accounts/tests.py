from django.apps import apps
from django.test import TestCase

from apps.accounts import urls as account_urls


class AccountsAppTests(TestCase):
    def test_accounts_app_is_registered(self):
        config = apps.get_app_config("accounts")
        self.assertEqual(config.name, "apps.accounts")

    def test_accounts_urlpatterns_defined(self):
        self.assertIsInstance(account_urls.urlpatterns, list)
