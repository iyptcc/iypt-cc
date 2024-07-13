from rest_framework import routers

from apps.account.api.urls import router as account_router
from apps.printer.api.urls import router as printer_router

router = routers.DefaultRouter()
router.registry.extend(printer_router.registry)
router.registry.extend(account_router.registry)
