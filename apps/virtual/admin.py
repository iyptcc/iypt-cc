from django.contrib import admin

from .models import BBBGuest, BBBInstance, Hall, HallRole, Stream, StreamEdgeServer

# Register your models here.

admin.site.register(BBBInstance)
admin.site.register(BBBGuest)
admin.site.register(Hall)
admin.site.register(HallRole)
admin.site.register(Stream)
admin.site.register(StreamEdgeServer)
