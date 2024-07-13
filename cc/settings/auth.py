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
    {
        'NAME': 'django_pwned_passwords.password_validation.PWNEDPasswordValidator'
    },
]

PWNED_VALIDATOR_FAIL_SAFE = False
PWNED_VALIDATOR_URL = "http://haveibeenpwned-api:5000/range/{short_hash}"

LOGIN_REDIRECT_URL = 'account:profile'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_URL = 'login'

AUTHENTICATION_BACKENDS = [
    'apps.account.backends.TournamentModelBackend'
]

# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"

ACCOUNT_ACTIVATION_DAYS = 7

OAUTH2_PROVIDER = {
    'user': {
        'read': 'Read user data',
        'write': 'Write user data',
    },
    'PKCE_REQUIRED': False,
}
