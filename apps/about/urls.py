from django.urls import path, re_path

from .views import help, info, tos

app_name = "about"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("info", info, name="info"),
    path("tos", tos, name="tos"),
    re_path(r"^", help, name="help"),
]
