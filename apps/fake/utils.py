from django.contrib.auth.models import User

from apps.account.models import ActiveUser, Attendee, ParticipationRole
from apps.team.models import Team, TeamMember, TeamRole
from apps.tournament.models import Origin


def _create_user(mytrn, **kwargs):
    new_user = User.objects.create_user(**kwargs)
    au = ActiveUser.objects.create(user=new_user)
    att = Attendee.objects.get_or_create(active_user=au, tournament=mytrn)[0]
    return att


def _create_team(mytrn, t):
    origin = Origin.objects.get_or_create(name=t.country, tournament=mytrn)[0]

    team = Team.objects.get_or_create(origin=origin, tournament=mytrn)[0]

    cap_teamrole = TeamRole.objects.get(tournament=mytrn, type=TeamRole.CAPTAIN)
    mem_teamrole = TeamRole.objects.get(tournament=mytrn, type=TeamRole.MEMBER)
    lead_teamrole = TeamRole.objects.get(tournament=mytrn, type=TeamRole.LEADER)

    student_prole = ParticipationRole.objects.get(
        tournament=mytrn, type=ParticipationRole.STUDENT
    )
    lead_prole = ParticipationRole.objects.get(
        tournament=mytrn, type=ParticipationRole.TEAM_LEADER
    )

    for num, m in enumerate(t.members):
        # log.append("create user: %s" % m.username)
        ctr = 0
        username = m.username
        while User.objects.filter(username=username).exists():
            ctr += 1
            username = "%s-%d" % (m.username, ctr)

            # log.append("use alternative username %s" % username)
        m.username = username

        att = _create_user(
            mytrn,
            username=username,
            email="%s@cc.dev.iypt.org" % username,
            first_name=m.first_name,
            last_name=m.last_name,
        )
        att.roles.add(student_prole)
        if num == 0:
            TeamMember.objects.get_or_create(
                attendee=att, team=team, role=cap_teamrole
            )[0]
        else:
            TeamMember.objects.get_or_create(
                attendee=att, team=team, role=mem_teamrole
            )[0]

    for num, tl in enumerate(t.teamleaders):
        ctr = 0
        username = tl.username
        while User.objects.filter(username=username).exists():
            ctr += 1
            username = "%s-%d" % (tl.username, ctr)
        tl.username = username

        att = _create_user(
            mytrn,
            username=username,
            email="%s@cc.dev.iypt.org" % username,
            first_name=tl.first_name,
            last_name=tl.last_name,
        )
        att.roles.add(lead_prole)
        TeamMember.objects.get_or_create(attendee=att, team=team, role=lead_teamrole)[0]
