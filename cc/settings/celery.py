# Celery settings
import os

CELERY_BROKER_URL = 'amqp://guest:guest@localhost//'
if "IN_DOCKER" in os.environ:
    CELERY_BROKER_URL = "amqp://" + os.environ['RABBITMQ_DEFAULT_USER'] + ":" + os.environ['RABBITMQ_DEFAULT_PASS'] + "@" + os.environ['RABBITMQ_SERVICE'] + "//"

# Only add pickle to this list if your broker is secured
# from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
# CELERY_RESULT_BACKEND = 'db+sqlite:///results.sqlite'
CELERY_TASK_SERIALIZER = 'json'

CELERY_RESULT_BACKEND = 'django-db'

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

if 'XELATEX_IMAGE_NAME' in os.environ:
    XELATEX_IMAGE_NAME = os.environ['XELATEX_IMAGE_NAME']

CELERY_BEAT_SCHEDULE = {
    'syncbbb': {
        'task': 'apps.virtual.tasks.syncbbb',
        'schedule': 30,  # crontab(minute=59, hour=23),
        # 'args': (*args)
    },
}
