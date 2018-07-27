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
from django.conf.urls import include, url
from django.contrib import admin
from django.template.response import TemplateResponse
from django.views.generic.base import RedirectView

from apps.account.registration import RegistrationView

favicon_view = RedirectView.as_view(url='/static/cc-favicon.ico', permanent=True)
robots_view = RedirectView.as_view(url='/static/robots.txt', permanent=True)

def handler500(request,*args,**kwargs):
    """500 error handler which includes ``request`` in the context.

    Templates: `500.html`
    Context: None
    """

    context = {'request': request}
    template_name = 'dashboard/500.html'  # You need to create a 500.html template.
    return TemplateResponse(request, template_name, context, status=500)

def handler404(request,*args,**kwargs):
    context = {'request': request}
    template_name = 'dashboard/404.html'  # You need to create a 500.html template.
    return TemplateResponse(request, template_name, context, status=404)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^account/', include('apps.account.urls', namespace='account')),
    url(r'^plan/', include('apps.plan.urls', namespace='plan')),
    url(r'^jury/', include('apps.jury.urls', namespace='jury')),
    url(r'^dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    url(r'^fight/', include('apps.fight.urls', namespace='fight')),
    url(r'^tournament/', include('apps.tournament.urls', namespace='tournament')),
    url(r'^bank/', include('apps.bank.urls', namespace='bank')),
    url(r'^schedule/', include('apps.schedule.urls', namespace='schedule')),
    url(r'^printer/', include('apps.printer.urls', namespace='printer')),
    url(r'^postoffice/', include('apps.postoffice.urls', namespace='postoffice')),
    url(r'^management/', include('apps.management.urls', namespace='management')),
    url(r'^about/', include('apps.about.urls', namespace='about')),
    url(r'^registration/', include('apps.registration.urls', namespace='registration')),
    url(r'^auth/register/$', RegistrationView.as_view(), name='registration_register'),
    url(r'^auth/', include('registration.backends.hmac.urls')),
    url(r'^favicon\.ico$', favicon_view),
    url(r'^robots\.txt$', robots_view),
    url(r'^feedback/', include("tellme.urls")),
    url(r'^hijack/', include('hijack.urls', namespace='hijack')),
    url(r'^', include('apps.result.urls', namespace='result')),
]

if settings.DEV:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
