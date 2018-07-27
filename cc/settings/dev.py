import os

from .base import ALLOWED_HOSTS, BASE_DIR, INSTALLED_APPS, MIDDLEWARE

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.join(BASE_DIR, 'db' ),'db.sqlite3'),
        #'TEST': {'NAME': os.path.join(os.path.join(BASE_DIR, 'db' ),'db.utest.sqlite3')}
    }
}

INSTALLED_APPS += [
    'django_extensions',
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]+ MIDDLEWARE

INTERNAL_IPS = ['127.0.0.1']

DEBUG = True

ALLOWED_HOSTS += ["localhost"]

DEV = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'iyptcc-snowflake',
    },
    'results': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'iyptcc-snowflake',
    }
}
