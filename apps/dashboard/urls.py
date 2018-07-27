from django.conf import settings
from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from . import views

app_name='dashboard'

urlpatterns = [

    url(r'^message/(?P<id>\w+)$', views.index, name='show_message'),
    url(r'^messages$', views.index, name='all_messages'),

    url(r'^notification/(?P<id>\w+)$', views.index, name='show_notification'),
    url(r'^notifications$', views.index, name='all_notifications'),

    url(r'^task/(?P<id>\w+)$', views.index, name='show_task'),
    url(r'^tasks$', views.index, name='all_tasks'),

    url(
        r'^password_change/$',
        auth_views.password_change,
        {
            'template_name': 'dashboard/user/password_change_form.html',
            'post_change_redirect': 'dashboard:password'
        },
        name='password'
    ),
    #
    # url(
    #     r'^login$',
    #     auth_views.login,
    #     {
    #         'template_name': 'dashboard/user/login.html',
    #     },
    #     name='login'
    # ),
    #
    # url(
    #     r'^logout$',
    #     auth_views.logout_then_login,
    #     {
    #         'login_url': '/'
    #     },
    #     name='logout'
    # ),

    url(r'^password_reset/$', auth_views.password_reset,
        {
            "template_name":"dashboard/user/password_reset_form.html",
            "post_reset_redirect":"dashboard:password_reset_done",
            "email_template_name":"dashboard/user/password_reset_email.html"
        },
        name='password_reset'),
    url(r'^password_reset/done/', auth_views.password_reset_done,
        {
            "template_name": "dashboard/user/password_reset_done.html",
        },
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        {
            "post_reset_redirect": "dashboard:password_reset_complete",
        },name='password_reset_confirm'),
    url(r'^reset/done/', auth_views.password_reset_complete, name='password_reset_complete'),

    url(r'^results/login/(?P<t_slug>[-\w]+)$', views.Simplelogin.as_view(), name="simplelogin"),
    url(r'^results/logout$', views.simplelogout, name="simplelogout"),

    url(r'^menu/open/(?P<uid>[0-9]+)$', views.openmenu,name="open_menu"),
    url(r'^menu/close/(?P<uid>[0-9]+)$', views.closemenu,name="close_menu"),
    url(r'^menu/collapse/(?P<opt>(on|off))$', views.collapsemenu,name="collapse_menu"),

    url(r'^flag/(?P<t_slug>[-\w]+)/(?P<o_slug>[-\w]+)', views.FlagImageView.as_view(), name="flag"),

    url(r'', include('django.contrib.auth.urls')),

]
