from django.contrib import admin

from .models import ClockState, ScanProcessing

# Register your models here.

admin.site.register(ClockState)
admin.site.register(ScanProcessing)
