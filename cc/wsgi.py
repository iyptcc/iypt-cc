"""
WSGI config for cc project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc.settings")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(BASE_DIR)

if 'IN_DOCKER' not in os.environ:
    activate_env=os.path.join(BASE_DIR, 'env', 'bin', 'activate_this.py')
    with open(activate_env) as f:
        code = compile(f.read(), "activate_this.py", 'exec')
        exec(code, dict(__file__=activate_env))


from django.core.wsgi import get_wsgi_application


application = get_wsgi_application()
