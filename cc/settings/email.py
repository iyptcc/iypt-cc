
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'cc@iypt.org'
# EMAIL_HOST_PASSWORD = 'secret'
try:
    from .secret_email import *  # noqa: F401,F403
except ImportError:
    pass

EMAIL_USE_TLS = True

EMAIL_FROM = "cc@iypt.org"
