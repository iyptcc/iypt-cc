from django.conf.global_settings import DATETIME_INPUT_FORMATS

DATETIME_INPUT_FORMATS += ['%Y-%m-%dT%H:%M:%S%z',
                           '%Y-%m-%dT%H:%M%z',]
