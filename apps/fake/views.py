from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from apps.account.models import ParticipationRole
from apps.dashboard.test_categories import fakedata

from .forms import PersonForm
from .utils import _create_team, _create_user


@login_required
def actions(request):
    personform = PersonForm()
    return render(
        request, "fake/overview.html", context={"forms": [("fake:persons", personform)]}
    )


@login_required
def generate_persons(request):
    if request.method == "POST":
        mytrn = request.user.profile.tournament
        form = PersonForm(request.POST)
        log = []
        if form.is_valid():
            juror_prole = ParticipationRole.objects.get(
                tournament=mytrn, type=ParticipationRole.JUROR
            )
            ass_prole = ParticipationRole.objects.get(
                tournament=mytrn, type=ParticipationRole.FIGHT_ASSISTANT
            )

            trn = fakedata.FakeTournament(
                "en_GB",
                form.cleaned_data["teams"],
                form.cleaned_data["team_members"],
                form.cleaned_data["indep_jur"],
                form.cleaned_data["local_jur"],
                form.cleaned_data["f_ass"],
            )

            for t in trn.teams:
                _create_team(mytrn, t)

            for j in trn.independent_jurors + trn.local_jurors:
                ctr = 0
                username = j.username
                while User.objects.filter(username=username).exists():
                    ctr += 1
                    username = "%s-%d" % (j.username, ctr)
                j.username = username

                att = _create_user(
                    mytrn,
                    username=username,
                    email="%s@cc.dev.iypt.org" % username,
                    first_name=j.first_name,
                    last_name=j.last_name,
                )
                att.roles.add(juror_prole)

            for j in trn.fight_assistants:
                ctr = 0
                username = j.username
                while User.objects.filter(username=username).exists():
                    ctr += 1
                    username = "%s-%d" % (j.username, ctr)
                j.username = username

                att = _create_user(
                    mytrn,
                    username=username,
                    email="%s@cc.dev.iypt.org" % username,
                    first_name=j.first_name,
                    last_name=j.last_name,
                )
                att.roles.add(ass_prole)

        else:
            log.append("form not valid")

        return redirect("fake:actions")
