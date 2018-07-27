from django.contrib import admin
from ordered_model.admin import OrderedModelAdmin

from .models import (Application, AttendeeProperty, AttendeePropertyValue, Property, PropertyChoice, UserProperty,
                     UserPropertyValue)


class APVAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = AttendeePropertyValue.unconfirmed.all()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

admin.site.register(Application)
admin.site.register(Property)
admin.site.register(PropertyChoice)
admin.site.register(UserProperty, OrderedModelAdmin)
admin.site.register(UserPropertyValue)
admin.site.register(AttendeeProperty)
admin.site.register(AttendeePropertyValue, APVAdmin)
