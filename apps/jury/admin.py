from django.contrib import admin
from ordered_model.admin import OrderedModelAdmin

from .models import (
    AssignResult,
    GradingGroup,
    GradingSheet,
    GroupGrade,
    Juror,
    JurorGrade,
    JurorOccupation,
    JurorRole,
    JurorSession,
    PossibleJuror,
)

# Register your models here.

admin.site.register(Juror)
admin.site.register(PossibleJuror)
admin.site.register(JurorRole)


class JurorSessionAdmin(admin.ModelAdmin):
    list_display = ["juror", "fight", "role", "juror__attendee__tournament"]
    list_filter = ["role__type", "juror__attendee__tournament"]
    search_fields = [
        "juror__attendee__active_user__user__first_name",
        "juror__attendee__active_user__user__last_name",
    ]


admin.site.register(JurorSession, JurorSessionAdmin)
admin.site.register(JurorGrade)

admin.site.register(AssignResult)
admin.site.register(GradingSheet)

admin.site.register(GradingGroup, OrderedModelAdmin)
admin.site.register(GroupGrade)

admin.site.register(JurorOccupation, OrderedModelAdmin)
