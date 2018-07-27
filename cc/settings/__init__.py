from .base import *
from .auth import *
from .db import *
from .email import *

from .i18n import *
from .celery import *

from .date import *

from .logging import *

import socket
import os

if socket.gethostname() == 'larix':
    from .dev import *
else:
    from .production import *

if "FORCE_DEBUG" in os.environ:
    DEBUG = True

if "DEV_DOCKER" in os.environ:
    ALLOWED_HOSTS += ["localhost"]

if "IN_DOCKER" in os.environ:
    from .cache_redis import *
    from .channels_redis import *
else:
    from .cache import *
    from .channels import *
