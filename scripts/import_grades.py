import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc.settings")

print(os.path.abspath(__file__ + "/../../"))

sys.path.append(os.path.abspath(__file__ + "/../../"))

import django
django.setup()

from django.contrib.auth.models import User
from apps.account.models import ActiveUser, Attendee
from apps.tournament.models import Tournament, Problem
from apps.team.models import Team, TeamMember, TeamRole

from apps.plan.models import Room, Round, Fight, FightRole, Stage, StageAttendance, TeamPlaceholder
from apps.jury.models import Juror, JurorSession, JurorRole, JurorGrade

iypt2016 = Tournament.objects.get_or_create(name="IYPT 2016", slug="iypt2016")[0]

rep = FightRole.objects.get_or_create(name="Reporter", type=FightRole.REP,factor=3.0, tournament = iypt2016)[0]
opp = FightRole.objects.get_or_create(name="Opponent", type=FightRole.OPP,factor=2.0, tournament = iypt2016)[0]
rev = FightRole.objects.get_or_create(name="Reviewer", type=FightRole.REV,factor=1.0, tournament = iypt2016)[0]
obs = FightRole.objects.get_or_create(name="Observer", type=FightRole.OBS,factor=0.0, tournament = iypt2016)[0]

chairrole = JurorRole.objects.get_or_create(name="Chair", type=JurorRole.CHAIR , tournament = iypt2016)
jurorrole = JurorRole.objects.get_or_create(name="Juror", type=JurorRole.JUROR , tournament = iypt2016)
jnr={}

with open(sys.argv[2]) as f:
    for line in f:
        parts = line.split(",")

        jnr[parts[1]+"-"+parts[3].strip()]=parts[2]


with open(sys.argv[1]) as f:
    for line in f:
        parts = line.split(",")

        #is this format fucking kidding me???

        fi = Fight.objects.get(pk=int(parts[1]))

        st = fi.stage_set.get(order=int(parts[2]))



        #hacky hopy (don't mess too much or it will bite your ass)
        juror = fi.jurorsession_set.get(juror__attendee__active_user__user__username=jnr[parts[1]+"-"+parts[3].strip()])

        if int(parts[4]) == 1: #rep
            JurorGrade.objects.get_or_create(juror_session=juror, stage_attendee=st.rep_attendance, grade=float(parts[5]),valid=True)
        if int(parts[4]) == 2: #opp
            JurorGrade.objects.get_or_create(juror_session=juror, stage_attendee=st.opp_attendance, grade=float(parts[5]),valid=True)
        if int(parts[4]) == 3: #rev
            JurorGrade.objects.get_or_create(juror_session=juror, stage_attendee=st.rev_attendance, grade=float(parts[5]),valid=True)
