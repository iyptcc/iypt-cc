from django.contrib import admin

from .models import AssignResult, Juror, JurorGrade, JurorRole, JurorSession, PossibleJuror

# Register your models here.

admin.site.register(Juror)
admin.site.register(PossibleJuror)
admin.site.register(JurorRole)
admin.site.register(JurorSession)
admin.site.register(JurorGrade)

admin.site.register(AssignResult)
