from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path, reverse_lazy

from . import views

app_name = "dashboard"

urlpatterns = [
    re_path(r"^message/(?P<id>\w+)$", views.index, name="show_message"),
    path("messages", views.index, name="all_messages"),
    re_path(r"^notification/(?P<id>\w+)$", views.index, name="show_notification"),
    path("notifications", views.index, name="all_notifications"),
    re_path(r"^task/(?P<id>\w+)$", views.index, name="show_task"),
    path("tasks", views.index, name="all_tasks"),
    path(
        "password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="dashboard/user/password_change_form.html",
            success_url=reverse_lazy("dashboard:password_changed"),
        ),
        name="password",
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
    path("password_changed/", views.password_change_done, name="password_changed"),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="dashboard/user/password_reset_form.html",
            success_url=reverse_lazy("dashboard:password_reset_done"),
            email_template_name="dashboard/user/password_reset_email.html",
        ),
        name="password_reset",
    ),
    re_path(
        r"^password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="dashboard/user/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    re_path(
        r"^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        auth_views.PasswordResetConfirmView.as_view(
            success_url=reverse_lazy("dashboard:password_reset_complete")
        ),
        name="password_reset_confirm",
    ),
    re_path(
        r"^reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    re_path(
        r"^results/login/(?P<t_slug>[-\w]+)$",
        views.Simplelogin.as_view(),
        name="simplelogin",
    ),
    path("results/logout", views.simplelogout, name="simplelogout"),
    path("menu/open/<int:uid>", views.openmenu, name="open_menu"),
    path("menu/close/<int:uid>", views.closemenu, name="close_menu"),
    re_path(
        r"^menu/collapse/(?P<opt>(on|off))$", views.collapsemenu, name="collapse_menu"
    ),
    re_path(
        r"^flag/(?P<t_slug>[-\w]+)/(?P<o_slug>[-\w]+)",
        views.FlagImageView.as_view(),
        name="flag",
    ),
    re_path(r"", include("django.contrib.auth.urls")),
]
