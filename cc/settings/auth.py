# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_REDIRECT_URL = 'account:profile'
LOGOUT_REDIRECT_URL = 'auth_login'
LOGIN_URL = 'auth_login'

AUTHENTICATION_BACKENDS = [
    'apps.account.backends.TournamentModelBackend'
]

#SESSION_ENGINE = "django.contrib.sessions.backends.cache"
#SESSION_CACHE_ALIAS = "default"

ACCOUNT_ACTIVATION_DAYS = 7

HIJACK_LOGIN_REDIRECT_URL = '/account/profile/'
HIJACK_LOGOUT_REDIRECT_URL = '/management/users/'

HIJACK_USE_BOOTSTRAP = True
