import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ.get("PROCEZO_SECRET_KEY", "development-only-insecure-key")
DEBUG = False
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("PROCEZO_ALLOWED_HOSTS", "").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "platform_api",
    "identity",
    "audit",
    "cases",
    "intelligence",
    "documents",
    "requests_app",
    "inspections",
    "decisions",
    "reporting",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "platform_api.middleware.RequestIdMiddleware",
]
ROOT_URLCONF = "procezo.urls"
CSRF_FAILURE_VIEW = "platform_api.csrf.csrf_failure"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "procezo.wsgi.application"
db_engine = os.environ.get("PROCEZO_DB_ENGINE", "sqlite")
if db_engine not in {"sqlite", "postgresql"}:
    raise ImproperlyConfigured("PROCEZO_DB_ENGINE doit être sqlite ou postgresql")
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ.get("PROCEZO_DB_PATH", str(BASE_DIR / "db.sqlite3")), "OPTIONS": {"timeout": 5}}}
if db_engine == "postgresql":
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": os.environ.get("PROCEZO_PG_NAME", "procezo"), "USER": os.environ.get("PROCEZO_PG_USER", "procezo"), "PASSWORD": os.environ.get("PROCEZO_PG_PASSWORD", ""), "HOST": os.environ.get("PROCEZO_PG_HOST", "localhost"), "PORT": os.environ.get("PROCEZO_PG_PORT", "5432")}}
PROCEZO_PRIVATE_FILES_ROOT = os.environ.get("PROCEZO_PRIVATE_FILES_ROOT", str(BASE_DIR / "private"))
PROCEZO_CLAMSCAN_PATH = os.environ.get("PROCEZO_CLAMSCAN_PATH", "")
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SAMESITE = "Lax"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "platform_api.pagination.StandardPagination",
    "EXCEPTION_HANDLER": "platform_api.errors.exception_handler",
}
SPECTACULAR_SETTINGS = {"TITLE": "Procezo API", "VERSION": "1.4.0", "SERVE_INCLUDE_SCHEMA": False, "COMPONENT_SPLIT_PATCH": False}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"safe_json": {"()": "platform_api.logging.SafeJSONFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe_json"}},
    "loggers": {"procezo.requests": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
