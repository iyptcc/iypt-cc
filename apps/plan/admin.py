from django.contrib import admin

from .models import Fight, FightRole, Room, Round, Stage, StageAttendance, TeamPlaceholder

# Register your models here.

admin.site.register(Fight, list_display = ['room', 'round'])
admin.site.register(StageAttendance, list_display = ['stage', 'team', 'role'])
admin.site.register(FightRole, list_display = ['name', 'factor'])
admin.site.register(Stage, list_display = ['order', 'fight'])
admin.site.register(Room, list_display = ['name', 'location', 'tournament'] )
admin.site.register(Round, list_display = ['order', 'tournament', 'type'])
admin.site.register(TeamPlaceholder, list_display = ['name', 'tournament'])
