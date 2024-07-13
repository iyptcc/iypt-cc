

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'apps.account.api.authentication.TrnTokenAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    )
}
