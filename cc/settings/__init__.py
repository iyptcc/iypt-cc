from .base import *  # noqa: F403
from .auth import *  # noqa: F403
from .db import *  # noqa: F403
from .email import *  # noqa: F403

from .i18n import *  # noqa: F403
from .celery import *  # noqa: F403

from .date import *  # noqa: F403

from .logging import *  # noqa: F403

from .drf import *  # noqa: F403

from .mattermost import *  # noqa: F403

import socket
import os

if "IN_DOCKER" in os.environ:
    from .cache_redis import *  # noqa: F403,F401
    from .channels_redis import *  # noqa: F403,F401
else:
    from .cache import *  # noqa: F403,F401
    from .channels import *  # noqa: F403,F401

if socket.gethostname() == 'larix':
    from .dev import *  # noqa: F403
else:
    from .production import *  # noqa: F403

if "FORCE_DEBUG" in os.environ:
    DEBUG = True

if "DEV_DOCKER" in os.environ:
    ALLOWED_HOSTS += ["localhost"]  # noqa: F405
