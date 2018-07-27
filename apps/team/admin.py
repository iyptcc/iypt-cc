from django.contrib import admin

from .models import Team, TeamMember, TeamRole

# Register your models here.

admin.site.register(Team)
admin.site.register(TeamRole, list_display = ['name', 'tournament'])
admin.site.register(TeamMember, list_display = ['team', 'attendee'])
