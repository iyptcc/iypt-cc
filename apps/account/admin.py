from django.contrib import admin

from .models import ActiveUser, ApiUser, Attendee, ParticipationRole, Token


class AttendeeAdmin(admin.ModelAdmin):
    list_display = ["active_user", "tournament"]
    filter_horizontal = ("groups", "roles")


admin.site.register(Attendee, AttendeeAdmin)


class ActiveUserAdmin(admin.ModelAdmin):
    list_display = ["user", "get_full_name", "tournament", "get_tournaments"]

    def get_tournaments(self, obj):
        return ", \n".join([str(t) for t in obj.tournaments.all()])

    def get_full_name(self, obj):
        return "%s %s" % (obj.user.first_name, obj.user.last_name)


admin.site.register(ActiveUser, ActiveUserAdmin)
admin.site.register(ParticipationRole)
admin.site.register(ApiUser)
admin.site.register(Token)
