import importlib
from django.test import SimpleTestCase


REQUIRED_PACKAGES = [
    ("django", "django"),
    ("djangorestframework", "rest_framework"),
    ("psycopg2-binary", "psycopg2"),
    ("dj-database-url", "dj_database_url"),
    ("python-decouple", "decouple"),
    ("nba_api", "nba_api"),
    ("requests", "requests"),
]


class RequirementsTest(SimpleTestCase):
    def test_all_required_packages_importable(self):
        for package_name, import_name in REQUIRED_PACKAGES:
            with self.subTest(package=package_name):
                try:
                    importlib.import_module(import_name)
                except ImportError:
                    self.fail(
                        f"Package '{package_name}' "
                        f"(import '{import_name}') is not installed"
                    )
