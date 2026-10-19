"""Test settings: fast hashers, eager Celery, in-memory stores.

Set DEEPLRN_DATABASE_URL to run the suite against PostgreSQL (CI does this);
otherwise an in-memory SQLite database is used.
"""

from .base import *  # noqa: F403
from .base import env

SECRET_KEY = "test-only-insecure-key"
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

_database_url = env.str("DEEPLRN_DATABASE_URL", default="")
if _database_url:
    DATABASES = {"default": env.db_url_config(_database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "TEST": {"NAME": ":memory:"},
        }
    }

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "deeplrn-tests",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}
WHITENOISE_KEEP_ONLY_FILES = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
