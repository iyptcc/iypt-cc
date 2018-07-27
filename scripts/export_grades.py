import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc.settings")

print(os.path.abspath(__file__ + "/../../"))

sys.path.append(os.path.abspath(__file__ + "/../../"))

import django
django.setup()

from apps.tournament.models import Tournament, Problem

from apps.jury.models import JurorGrade

import yaml

from pprint import pprint

trn = Tournament.objects.get(slug=sys.argv[1])

print(trn)

problems = Problem.objects.filter(tournament=trn)

grades = []

for round in trn.round_set.all():

    round_grades = []

    for fight in round.fight_set.all():

        fight_grades = {"stages":[],"room":fight.room.name}
        for stage in fight.stage_set.all():

            stage_grades = {"rejected":[], "teams":{}}

            try:
                stage_grades["presented"] = stage.presented.number
            except:
                pass

            for rej in stage.rejections.all():
                stage_grades["rejected"].append(rej.number)

            for att in [stage.rep_attendance, stage.opp_attendance, stage.rev_attendance]:

                stage_grades["teams"][att.role.name] = {"grades":[]}
                stage_grades["teams"][att.role.name]["team"] = att.team.origin.name
                try:
                    stage_grades["teams"][att.role.name]["person"]= att.active_person.attendee.full_name
                except:
                    pass


                for jur in stage.fight.jurorsession_set.all():
                    try:
                        jg = JurorGrade.objects.get(juror_session=jur, stage_attendee=att)
                        stage_grades["teams"][att.role.name]["grades"].append([jur.juror.attendee.full_name,int(jg.grade)])
                    except:
                        pass

            fight_grades["stages"].append(stage_grades)
        round_grades.append(fight_grades)
    grades.append(round_grades)

with open(sys.argv[2],"w") as out:
    yaml.dump(grades,out)

