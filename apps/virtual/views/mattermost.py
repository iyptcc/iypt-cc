import mattermostdriver
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect
from mattermostdriver import Driver
from mattermostdriver.exceptions import ResourceNotFound

from apps.plan.models import Fight


@login_required
@permission_required("plan.change_fight_operator")
def update_channel(request, fight_id):
    fight = get_object_or_404(
        Fight, pk=fight_id, round__tournament=request.user.profile.tournament
    )

    mm = Driver(
        {
            "url": settings.MM_URL,
            "token": settings.MM_TOKEN,
            "port": settings.MM_PORT,
        }
    )
    mm.login()

    print("here in mm", mm)

    teams = mm.teams.get_teams()

    teamobjs = list(filter(lambda x: x["name"] == fight.round.tournament.slug, teams))
    if len(teamobjs) != 1:
        messages.add_message(
            request, messages.ERROR, "There is no Team for this Tournament"
        )
        print("not equal 1")
        return redirect("virtual:rooms")
    team_id = teamobjs[0]["id"]
    print("managed here")
    try:
        ch = mm.channels.create_channel(
            options={
                "team_id": team_id,
                "name": fight.chat_name,
                "display_name": "Fight %d %s" % (fight.round.order, fight.room.name),
                "purpose": "Reach all people in your room quickly",
                "type": "P",
            }
        )
    except mattermostdriver.exceptions.InvalidOrMissingParameters:
        ch = mm.channels.get_channel_by_name(team_id, fight.chat_name)
    print(ch)

    attendees = []
    stage1 = fight.stage_set.all()[0]
    fight_teams = [
        stage1.rep_attendance.team,
        stage1.opp_attendance.team,
        stage1.rev_attendance.team,
    ]
    if stage1.obs_attendance:
        teams.append(stage1.obs_attendance.team)

    for t in fight_teams:
        for att in t.get_students().all():
            attendees.append(att)

    for op in fight.operators.all():
        attendees.append(op)

    for j in fight.juror_set.all():
        attendees.append(j.attendee)

    emails = [a.active_user.user.email for a in attendees]
    emails.append(request.user.email)

    uniqmails = list(set(emails))

    ids = []
    for m in uniqmails:
        try:
            user = mm.users.get_user_by_email(m)
            ids.append(user["id"])
        except ResourceNotFound:
            pass

    for u in ids:
        try:
            mm.channels.add_user(ch["id"], options={"user_id": u})
        except:
            pass

    return redirect("virtual:rooms")
    # user = mm.users.get_user_by_email(request.user.email.lower())
    # mm.teams.add_user_to_team(team_id, options={"team_id": team_id, "user_id": user["id"]})

    # messages.add_message(request, messages.SUCCESS, "Added you to the chat team, you can log in at chat.iypt.org")
