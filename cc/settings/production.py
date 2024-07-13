
# ADMINS = [('Root', 'root@localhost')]
# SERVER_EMAIL = "root@localhost"

import os

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import BASE_DIR

release_hash = "unknown"
try:
    with open(os.path.join(os.path.dirname(BASE_DIR), "django-git/HEAD")) as f:
        release_hash = f.read()
except IOError:
    pass

dsnurl = "https://1234@sentry.iypt.org/2"
if "SENTRY_DSN_KEY" in os.environ:
    dsnurl = os.environ['SENTRY_DSN_KEY']

sentry_sdk.init(
    dsn=dsnurl,
    integrations=[DjangoIntegration()],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=1.0,

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,

    # By default the SDK will try to use the SENTRY_RELEASE
    # environment variable, or infer a git commit
    # SHA as release, however you may want to set
    # something more human-readable.
    release=release_hash,
)
