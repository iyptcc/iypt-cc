from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django.views import View

from apps.tournament.models import ScheduleTemplate

from .forms import GenerateForm
from .generator import cal_stats, fix_roles, generate_plan, plan_yaml_dump

# Create your views here.


def view(request):

    sts = ScheduleTemplate.objects.all()

    return render(request, "schedule/list.html", context={"schedules": sts})


def show(request, id):

    st = get_object_or_404(ScheduleTemplate, id=id)

    meet = [[[] for i in range(st.teams_nr())] for j in range(st.teams_nr())]

    max_cap = 0

    for room in st.templateroom_set.all():
        if room.capacity() > max_cap:
            max_cap = room.capacity()

    maxr_teams = [[] for i in range(st.teams_nr())]
    max_cap_max = 0

    for round in st.rounds.all():
        for fight in round.fights.all():
            teams = list(
                map(
                    lambda x: x[0],
                    fight.templateattendance_set.all().values_list("team"),
                )
            )
            short_fightstr = "%d - %s" % (round.order, fight.room.name)
            for team1 in teams:
                if fight.room.capacity() == max_cap:
                    maxr_teams[team1 - 1].append(short_fightstr)
                    if len(maxr_teams[team1 - 1]) > max_cap_max:
                        max_cap_max = len(maxr_teams[team1 - 1])
                for team2 in teams:
                    meet[team1 - 1][team2 - 1].append(short_fightstr)

    team_rooms = [[None for i in range(st.teams_nr())] for j in range(max_cap_max)]

    for idx, maxr_team in enumerate(maxr_teams):
        for ydx, room in enumerate(maxr_team):
            team_rooms[ydx][idx] = room

    equal_rows = 0
    for row in team_rooms:
        if all(map(bool, row)):
            equal_rows += 1

    return render(
        request,
        "schedule/show.html",
        context={
            "schedule": st,
            "meet": meet,
            "meet_ratio": 100.0 / (len(meet[0]) + 1),
            "team_rooms": team_rooms,
            "equal_room": equal_rows,
            "big_room_cap": max_cap,
        },
    )


class GenerateView(View):
    def get(self, request):
        form = GenerateForm()
        return render(request, "schedule/generate.html", context={"form": form})

    def post(self, request):

        form = GenerateForm(request.POST)

        if form.is_valid():
            teams = form.cleaned_data["teams"]
            rounds = form.cleaned_data["rounds"]
            simulation = form.cleaned_data["simulation"]
            plan = generate_plan(teams, rounds, simulation)

            # print(plan)

            plan = fix_roles(plan)

            meet, team_rooms, equal_rows, startrole = cal_stats(plan)

            roomnames = [chr(i) for i in range(ord("A"), ord("Z"))]

            yamlstr = plan_yaml_dump(teams, plan, roomnames)

            return render(
                request,
                "schedule/showgen.html",
                context={
                    "schedule": plan,
                    "roomnames": roomnames,
                    "meet": meet,
                    "meet_ratio": 100.0 / (len(meet[0]) + 1),
                    "team_rooms": team_rooms,
                    "equal_room": equal_rows,
                    "big_room_cap": 4,
                    "start_role": startrole,
                    "teamnr": teams,
                    "yaml": yamlstr,
                },
            )

        return render(request, "schedule/generate.html", context={"form": form})
