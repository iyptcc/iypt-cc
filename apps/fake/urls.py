from django.urls import path

from .forms import ImportForm
from .preview import ImportPreview
from .views import actions, generate_persons

app_name = "fake"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("actions/", actions, name="actions"),
    path("import/", ImportPreview(ImportForm), name="import"),
    path("fake/persons/", generate_persons, name="persons"),
]
