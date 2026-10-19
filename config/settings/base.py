"""Shared settings for all environments.

Secrets and deployment-specific values come from environment variables
(optionally from a `.env` file at the project root). Environment modules
(dev/prod/test) override anything that must differ; prod fails fast on
missing critical configuration.
"""

from decimal import Decimal
from pathlib import Path
from typing import Any

import environ
from csp.constants import NONCE, NONE, SELF

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env()
if (BASE_DIR / ".env").is_file():
    environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env.str("DEEPLRN_SECRET_KEY", default="dev-only-insecure-key-do-not-use-in-prod")
DEBUG = env.bool("DEEPLRN_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DEEPLRN_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DEEPLRN_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "whitenoise.runserver_nostatic",
    "csp",
    "common.apps.CommonConfig",
    "accounts.apps.AccountsConfig",
    "academics.apps.AcademicsConfig",
    "students.apps.StudentsConfig",
    "attendance.apps.AttendanceConfig",
    "results.apps.ResultsConfig",
    "billing.apps.BillingConfig",
    "dashboard.apps.DashboardConfig",
]

MIDDLEWARE = [
    "common.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "common.middleware.PermissionsPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Data stores
# ---------------------------------------------------------------------------
# A DEEPLRN_DATABASE_URL is the single switch for the database. When it is
# absent, dev/test fall back to SQLite; prod refuses to boot (see prod.py).
_database_url = env.str("DEEPLRN_DATABASE_URL", default="")
if _database_url:
    DATABASES = {"default": env.db_url_config(_database_url)}
else:
    DATABASES = {"default": env.db_url_config(f"sqlite:///{(BASE_DIR / 'db.sqlite3').as_posix()}")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DEEPLRN_DB_CONN_MAX_AGE", default=60)

_redis_url = env.str("DEEPLRN_REDIS_URL", default="")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "deeplrn-default",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
CACHE_TTL = env.int("DEEPLRN_CACHE_TTL", default=60)

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env.str("DEEPLRN_CELERY_BROKER_URL", default="redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = env.str("DEEPLRN_CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = env.str("DEEPLRN_TIME_ZONE", default="UTC")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 900
CELERY_BEAT_SCHEDULE = {
    "generate-monthly-invoices": {
        "task": "billing.tasks.generate_monthly_invoices",
        "schedule": "0 30 1 * *",  # 00:30 on the 1st of every month
    },
    "generate-weekly-attendance-report": {
        "task": "dashboard.tasks.generate_weekly_attendance_report",
        "schedule": "0 6 * * 1",  # 06:00 every Monday
    },
}
CELERY_TASK_ALWAYS_EAGER = env.bool("DEEPLRN_CELERY_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
_email_url = env.str("DEEPLRN_EMAIL_URL", default="")
if _email_url:
    vars().update(env.email_url(_email_url))
else:
    EMAIL_BACKEND = "django.core.email.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env.str(
    "DEEPLRN_DEFAULT_FROM_EMAIL", default="DEEPLRN <no-reply@deeplrn.local>"
)
EMAIL_TIMEOUT = env.int("DEEPLRN_EMAIL_TIMEOUT", default=10)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "dashboard:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Sessions are hardened in base and made secure in prod.
SESSION_COOKIE_NAME = "deeplrn_sessionid"
SESSION_COOKIE_AGE = env.int("DEEPLRN_SESSION_AGE_SECONDS", default=12 * 60 * 60)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_NAME = "deeplrn_csrftoken"
CSRF_COOKIE_SAMESITE = "Lax"

# Login throttling / account lockout (cache-backed, see accounts.security)
LOGIN_MAX_ATTEMPTS = env.int("DEEPLRN_LOGIN_MAX_ATTEMPTS", default=5)
LOGIN_LOCKOUT_SECONDS = env.int("DEEPLRN_LOGIN_LOCKOUT_SECONDS", default=900)

# Optional second-factor hook: dotted path to a callable(user, request) -> bool
# that returns True when the user requires a second factor. Empty disables it.
SECOND_FACTOR_HOOK = env.str("DEEPLRN_SECOND_FACTOR_HOOK", default="")

# ---------------------------------------------------------------------------
# Internationalisation / localisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env.str("DEEPLRN_LANGUAGE_CODE", default="en")
TIME_ZONE = env.str("DEEPLRN_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True
CURRENCY_CODE = env.str("DEEPLRN_CURRENCY_CODE", default="USD")

# ---------------------------------------------------------------------------
# Static files / storage
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
WHITENOISE_KEEP_ONLY_FILES = True

# Long-running jobs write artefacts (reports) here, never inside the web root.
REPORTS_ROOT = Path(env.str("DEEPLRN_REPORTS_ROOT", default=str(BASE_DIR / "reports")))

# ---------------------------------------------------------------------------
# UX defaults
# ---------------------------------------------------------------------------
PAGE_SIZE = env.int("DEEPLRN_PAGE_SIZE", default=25)
MAX_PAGE_SIZE = env.int("DEEPLRN_MAX_PAGE_SIZE", default=100)
ATTENDANCE_RISK_THRESHOLD = env.int("DEEPLRN_ATTENDANCE_RISK_THRESHOLD", default=75)
MONTHLY_INVOICE_AMOUNT = Decimal(env.str("DEEPLRN_MONTHLY_INVOICE_AMOUNT", default="500.00"))

# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, NONCE],
        "style-src": [SELF],
        "img-src": [SELF, "data:"],
        "font-src": [SELF],
        "connect-src": [SELF],
        "form-action": [SELF],
        "base-uri": [SELF],
        "frame-ancestors": [NONE],
        "object-src": [NONE],
    }
}

PERMISSIONS_POLICY = {
    "accelerometer": (),
    "camera": (),
    "geolocation": (),
    "gyroscope": (),
    "microphone": (),
    "payment": (),
    "usb": (),
}

# ---------------------------------------------------------------------------
# Logging (prod switches the console formatter to JSON)
# ---------------------------------------------------------------------------
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "common.logging.RequestIDFilter"}},
    "formatters": {
        "human": {"format": "{asctime} {levelname} {name} {request_id} {message}", "style": "{"},
        "json": {"()": "common.logging.JSONFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "human",
            "filters": ["request_id"],
        }
    },
    "root": {"handlers": ["console"], "level": env.str("DEEPLRN_LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "deeplrn": {
            "handlers": ["console"],
            "level": env.str("DEEPLRN_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SILENCED_SYSTEM_CHECKS: list[str] = []
