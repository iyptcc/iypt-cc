import os

MM_URL = "chat.iypt.org"
MM_PORT = 443

if "MM_TOKEN" in os.environ:
    SECRET_KEY = os.environ['MM_TOKEN']
else:
    try:
        from .secret_key import MM_TOKEN  # noqa: F401,F403
    except ImportError:
        pass
