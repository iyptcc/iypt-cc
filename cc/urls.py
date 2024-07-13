"""cc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from apps.account.registration import RegistrationView

from .api import router

favicon_view = RedirectView.as_view(url='/static/cc-favicon.ico', permanent=True)
robots_view = RedirectView.as_view(url='/static/robots.txt', permanent=True)


def handler500(request, *args, **kwargs):
    """500 error handler which includes ``request`` in the context.

    Templates: `500.html`
    Context: None
    """

    context = {'request': request}
    template_name = 'dashboard/500.html'  # You need to create a 500.html template.
    return TemplateResponse(request, template_name, context, status=500)


def handler404(request, *args, **kwargs):
    context = {'request': request}
    template_name = 'dashboard/404.html'  # You need to create a 500.html template.
    return TemplateResponse(request, template_name, context, status=404)


urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^account/', include('apps.account.urls', namespace='account')),
    re_path(r'^plan/', include('apps.plan.urls', namespace='plan')),
    re_path(r'^jury/', include('apps.jury.urls', namespace='jury')),
    re_path(r'^juryfeedback/', include('apps.feedback.urls', namespace='feedback')),
    re_path(r'^dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    re_path(r'^fight/', include('apps.fight.urls', namespace='fight')),
    re_path(r'^virtual/', include('apps.virtual.urls', namespace='virtual')),
    re_path(r'^tournament/', include('apps.tournament.urls', namespace='tournament')),
    re_path(r'^bank/', include('apps.bank.urls', namespace='bank')),
    re_path(r'^schedule/', include('apps.schedule.urls', namespace='schedule')),
    re_path(r'^printer/', include('apps.printer.urls', namespace='printer')),
    re_path(r'^postoffice/', include('apps.postoffice.urls', namespace='postoffice')),
    re_path(r'^management/', include('apps.management.urls', namespace='management')),
    re_path(r'^about/', include('apps.about.urls', namespace='about')),
    re_path(r'^registration/', include('apps.registration.urls', namespace='registration')),
    re_path(r'^fake/', include('apps.fake.urls', namespace='fake')),
    path('auth/register/', RegistrationView.as_view(), name='registration_register'),
    re_path(r'^auth/', include('django_registration.backends.activation.urls')),
    re_path(r'^auth/', include('django.contrib.auth.urls')),
    re_path(r'^oauth/', include('apps.account.oauth.urls', namespace='oauth2_provider')),
    re_path(r'^favicon\.ico$', favicon_view),
    re_path(r'^robots\.txt$', robots_view),
    re_path(r'^feedback/', include("tellme.urls")),
    re_path(r'^hijack/', include('hijack.urls', namespace='hijack')),
    re_path(r'^api/', include(router.urls)),
    path("captcha/", include('captcha.urls')),
    re_path(r'^', include('apps.result.urls', namespace='result')),
]

if settings.DEV:
    import debug_toolbar
    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]
