import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

if not os.environ.get("PROCEZO_SECRET_KEY") or SECRET_KEY == "development-only-insecure-key":
    raise ImproperlyConfigured("PROCEZO_SECRET_KEY est obligatoire en production")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("PROCEZO_ALLOWED_HOSTS est obligatoire en production")
if not os.environ.get("PROCEZO_DB_PATH"):
    raise ImproperlyConfigured("PROCEZO_DB_PATH est obligatoire en production")
if not os.path.isabs(os.environ["PROCEZO_DB_PATH"]):
    raise ImproperlyConfigured("PROCEZO_DB_PATH doit être absolu")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
