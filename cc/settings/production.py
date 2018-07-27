import os

import raven

from .base import BASE_DIR, MIDDLEWARE

release_hash = "unknown"
try:
    with open(os.path.join(os.path.dirname(BASE_DIR),"django-git/HEAD")) as f:
        release_hash = f.read()
except:
    pass

try:
    from .secret_sentry import *
except:
    pass

RAVEN_CONFIG = {
    'dsn': RAVEN_DSN,
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    'release': release_hash,
}

MIDDLEWARE = [
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
]+ MIDDLEWARE
