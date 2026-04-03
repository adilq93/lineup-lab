from django.conf import settings
from django.test import TestCase


class SettingsTest(TestCase):
    def test_installed_apps_includes_required(self):
        for app in ('ingestion', 'analytics', 'rest_framework'):
            self.assertIn(app, settings.INSTALLED_APPS)

    def test_secret_key_not_hardcoded_insecure_default(self):
        self.assertNotIn('django-insecure-', settings.SECRET_KEY)

    def test_database_default_engine(self):
        engine = settings.DATABASES['default']['ENGINE']
        self.assertTrue(
            engine.startswith('django.db.backends.'),
            msg=f"Unexpected DB engine: {engine}",
        )

    def test_debug_is_bool(self):
        self.assertIsInstance(settings.DEBUG, bool)
