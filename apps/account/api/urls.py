from rest_framework import routers

from .views import UserViewSet

router = routers.DefaultRouter()
router.register(r"v4/user", UserViewSet, basename="user")
