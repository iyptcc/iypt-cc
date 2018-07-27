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

from apps.result.utils import _fightpreview

import random

trn = Tournament.objects.get(slug=sys.argv[1])

print(trn)

problems = Problem.objects.filter(tournament=trn)

for round in trn.round_set(manager="selectives").all():
    for fight in round.fight_set.all():
        for stage in fight.stage_set.all():
            print(stage)
            prev = _fightpreview(stage.fight, use_cache=False)[stage.order - 1]
            print(prev['free'])
            print(prev["opp"])
            rejects = random.randint(0,2)
            prblms = random.sample(prev['free'], rejects+1)
            stage.presented = problems.get(number=prblms[0])
            stage.save()
            stage.rejections.clear()
            for rej in prblms[1:]:
                stage.rejections.add(problems.get(number=rej))
                pass

            for att in [stage.rep_attendance, stage.opp_attendance, stage.rev_attendance]:
                members = att.team.teammember_set.all()
                active = random.choice(members)
                att.active_person = active
                att.save()


                for jur in stage.fight.jurorsession_set.all():
                    try:
                        jg = JurorGrade.objects.get(juror_session=jur, stage_attendee=att)
                        jg.grade = random.randint(1, 10)
                        jg.valid = True
                        jg.save()
                    except:
                        JurorGrade.objects.create(juror_session=jur, stage_attendee=att, grade=random.randint(1,10), valid=True)
