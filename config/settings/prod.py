"""Production settings.

Fails fast unless the critical configuration is present:
DEEPLRN_SECRET_KEY, DEEPLRN_ALLOWED_HOSTS, DEEPLRN_DATABASE_URL,
DEEPLRN_REDIS_URL and DEEPLRN_CSRF_TRUSTED_ORIGINS must all be set.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env

SECRET_KEY = env.str("DEEPLRN_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("DEEPLRN_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DEEPLRN_ALLOWED_HOSTS must list at least one host in production.")

CSRF_TRUSTED_ORIGINS = env.list("DEEPLRN_CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "DEEPLRN_CSRF_TRUSTED_ORIGINS must list the site origin(s) in production."
    )

_database_url = env.str("DEEPLRN_DATABASE_URL")
DATABASES = {"default": env.db_url_config(_database_url)}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DEEPLRN_DB_CONN_MAX_AGE", default=60)

_redis_url = env.str("DEEPLRN_REDIS_URL")
if not _redis_url:
    raise ImproperlyConfigured("DEEPLRN_REDIS_URL is required in production (cache + sessions).")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": _redis_url,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DEEPLRN_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DEEPLRN_HSTS_SECONDS", default=63072000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365

LOGGING["formatters"]["console"] = LOGGING["formatters"]["json"]  # noqa: F405
LOGGING["handlers"]["console"]["formatter"] = "console"  # noqa: F405

_sentry_dsn = env.str("DEEPLRN_SENTRY_DSN", default="")
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,
        traces_sample_rate=env.float("DEEPLRN_SENTRY_TRACES_RATE", default=0.1),
        release=env.str("DEEPLRN_RELEASE", default="deeplrn@unknown"),
    )
