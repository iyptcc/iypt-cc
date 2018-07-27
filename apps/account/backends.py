from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from apps.account.models import ActiveUser


class TournamentModelBackend(ModelBackend):

    def _get_group_permissions(self, user_obj):
        user_groups_field = get_user_model()._meta.get_field('groups')
        user_groups_query = 'group__%s' % user_groups_field.related_query_name()

        # additional check if group is active

        try:
            active_groups = user_obj.profile.groups.all()
        except ActiveUser.DoesNotExist:
            active_groups = Group.objects.none()

        try:
            for r in user_obj.profile.active.roles.all():
                active_groups |= r.groups.all()
        except:
            pass


        return Permission.objects.filter(Q(group__in=active_groups) | Q(**{user_groups_query: user_obj}))
