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
admin.site.register(JurorSession)
admin.site.register(JurorGrade)

admin.site.register(AssignResult)
admin.site.register(GradingSheet)

admin.site.register(GradingGroup, OrderedModelAdmin)
admin.site.register(GroupGrade)

admin.site.register(JurorOccupation, OrderedModelAdmin)
