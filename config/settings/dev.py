"""Development settings: SQLite fallback, console email, verbose logging."""

from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = env.bool("DEEPLRN_DEBUG", default=True)
SECRET_KEY = env.str("DEEPLRN_SECRET_KEY", default="dev-only-insecure-key-do-not-use-in-prod")
ALLOWED_HOSTS = env.list("DEEPLRN_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"])

if not env.str("DEEPLRN_DATABASE_URL", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
WHITENOISE_KEEP_ONLY_FILES = False
