from django.contrib.auth.models import Permission
from django.db.models import Q


def _more_perm_than_group(user, group):
    gperm = set()
    for p in group.permissions.all():
        name = "%s.%s" % (p.content_type.app_label, p.codename)
        gperm.update([name])

    allperm = user.get_all_permissions()

    covered = gperm - allperm
    if len(covered):
        return False
    return True


def _more_perm_than_role(user, role):

    for g in role.groups.all():
        if not _more_perm_than_group(user, g):
            return False
    return True


def _is_superior_user(user, other_attendee):

    allperm = user.get_all_permissions()

    gperm = set()
    for p in Permission.objects.filter(
        Q(group__attendee=other_attendee)
        | Q(group__participationrole__attendee=other_attendee)
    ):
        name = "%s.%s" % (p.content_type.app_label, p.codename)
        gperm.update([name])

    covered = gperm - allperm
    if len(covered):
        return False
    return True
