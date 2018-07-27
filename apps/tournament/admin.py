from django.contrib import admin
from django.contrib.auth.models import Permission

from .models import Origin, Problem, ScheduleTemplate, TemplateAttendance, TemplateFight, TemplateRound, Tournament

# Register your models here.

admin.site.register(Tournament)
admin.site.register(Origin)
admin.site.register(Problem)

admin.site.register(ScheduleTemplate)
admin.site.register(TemplateRound)
admin.site.register(TemplateFight)
admin.site.register(TemplateAttendance)

admin.site.register(Permission)
