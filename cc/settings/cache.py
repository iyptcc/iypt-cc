# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
#         'LOCATION': '127.0.0.1:11211',
#     },
#     'results': {
#         'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
#         'LOCATION': '127.0.0.1:11211',
#     }
# }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': 'iyptcc-snowflake',
    },
    'results': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': 'iyptcc-snowflake',
    }
}
