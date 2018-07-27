# Celery settings
import os

CELERY_BROKER_URL = 'amqp://guest:guest@localhost//'
if "IN_DOCKER" in os.environ:
    CELERY_BROKER_URL = "amqp://"+os.environ['RABBITMQ_DEFAULT_USER']+":"+os.environ['RABBITMQ_DEFAULT_PASS']+"@"+os.environ['RABBITMQ_SERVICE']+"//"

#: Only add pickle to this list if your broker is secured
#: from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
# CELERY_RESULT_BACKEND = 'db+sqlite:///results.sqlite'
CELERY_TASK_SERIALIZER = 'json'

CELERY_RESULT_BACKEND = 'django-db'
