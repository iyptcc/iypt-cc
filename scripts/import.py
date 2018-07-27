import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc.settings")

print(os.path.abspath(__file__ + "/../../"))

sys.path.append(os.path.abspath(__file__ + "/../../"))

import django
django.setup()

from django.contrib.auth.models import User
from apps.account.models import ActiveUser, Attendee
from apps.tournament.models import Tournament, Problem, Origin
from apps.team.models import Team, TeamMember, TeamRole

from apps.plan.models import Room, Round, Fight, FightRole, Stage, StageAttendance, TeamPlaceholder
from apps.jury.models import Juror, JurorSession, JurorRole
from django.template.defaultfilters import slugify

iypt2016 = Tournament.objects.get_or_create(name="IYPT 2016", slug="iypt2016", results_access=Tournament.RESULTS_PUBLIC)[0]

root=ActiveUser.objects.get(user__username="root")
rootatt=Attendee.objects.get_or_create(active_user=root,tournament=iypt2016)[0]
root.active=rootatt
root.save()

placeholders={}

rep = FightRole.objects.get_or_create(name="Reporter", type=FightRole.REP,factor=3.0, tournament = iypt2016)[0]
opp = FightRole.objects.get_or_create(name="Opponent", type=FightRole.OPP,factor=2.0, tournament = iypt2016)[0]
rev = FightRole.objects.get_or_create(name="Reviewer", type=FightRole.REV,factor=1.0, tournament = iypt2016)[0]
obs = FightRole.objects.get_or_create(name="Observer", type=FightRole.OBS,factor=0.0, tournament = iypt2016)[0]

chairrole = JurorRole.objects.get_or_create(name="Chair", type=JurorRole.CHAIR , tournament = iypt2016)
jurorrole = JurorRole.objects.get_or_create(name="Juror", type=JurorRole.JUROR , tournament = iypt2016)

with open(sys.argv[2]) as f:
    for line in f:
        parts = line.split(",")

        if sys.argv[1] == 'users':

            user = None
            try:
                user = User.objects.create_user(parts[0],first_name=parts[2],last_name=parts[3])
                print("imported %s"%(user,))
            except:
                user = User.objects.get(username=parts[0])

            auser = None
            try:
                auser = ActiveUser.objects.create(user=user)
                print("create activeUser %s"%(auser,))
            except:
                auser = ActiveUser.objects.get(user=user)

            attendee = None

            try:
                attendee = Attendee.objects.create(active_user=auser,tournament=iypt2016)
            except:
                attendee = Attendee.objects.get(active_user=auser,tournament=iypt2016)

            auser.active = attendee
            auser.save()

        if sys.argv[1] == 'jurors':

            if parts[5].strip() == 'True':

                user = None
                try:
                    user = User.objects.create_user(parts[0],first_name=parts[2],last_name=parts[3])
                    print("imported %s"%(user,))
                except:
                    user = User.objects.get(username=parts[0])

                auser = ActiveUser.objects.get_or_create(user=user)

                attendee = Attendee.objects.get_or_create(active_user=auser[0],tournament=iypt2016)

                juror = Juror.objects.get_or_create(attendee = attendee[0])

        elif sys.argv[1] == 'jury':


            fi = Fight.objects.get(pk=int(parts[1]))

            j = Juror.objects.get(attendee__active_user__user__username = parts[2])

            if int(parts[3])==1:
                JurorSession.objects.get_or_create(juror=j, fight=fi, role=chairrole[0])
            else:
                JurorSession.objects.get_or_create(juror=j, fight=fi, role=jurorrole[0])



        elif sys.argv[1] == 'problems':

            print(parts[2])
            print(parts[3].strip())
            try:
                Problem.objects.create(pk=int(parts[0]),number=int(parts[2]),title=parts[3].strip(), tournament=iypt2016)
            except Exception as e:
                print(e)
                pass

        elif sys.argv[1] == 'teams':


            origin,cre = Origin.objects.get_or_create(name=parts[2].strip(), tournament=iypt2016)

            origin.short=slugify(origin.name)
            origin.save()

            try:
                Team.objects.create(tournament=iypt2016, origin=origin,pk=int(parts[0]))

            except Exception as e:
                print(e)
                pass

        elif sys.argv[1] == 'members':

            memberrole = TeamRole.objects.get_or_create(name="Pupil", tournament=iypt2016)[0]

            person = Attendee.objects.get(active_user__user__username=parts[2].strip(), tournament = iypt2016)
            team = Team.objects.get(pk=int(parts[1]))

            exists=False
            try:
                TeamMember.objects.get(attendee = person, team = team, role = memberrole)
                exists=True
            except:
                pass

            try:
                if not exists:
                    TeamMember.objects.create(attendee = person, team = team, role = memberrole)
            except Exception as e:
                print(e)
                pass

        elif sys.argv[1] == 'fights':
            # needs fix with import of stages
            print("---")

            room = Room.objects.get_or_create(name=parts[2],tournament=iypt2016)
            print(room[0])

            print(parts[7])

            ro = Round.objects.get_or_create(order=int(parts[7]),tournament=iypt2016, publish_ranking=True)
            print(ro[0])

            fi = Fight.objects.get_or_create(pk=int(parts[0]), room=room[0], round=ro[0], publish_grades=True, publish_preview=True)
            print(fi)

            # tplhds=[]
            #
            # for i in parts[3:7]:
            #     if i:
            #         if i not in placeholders:
            #             nxtelem=len(placeholders)+1
            #             placeholders[i]=nxtelem
            #             tp = TeamPlaceholder.objects.get_or_create(name="Team %d"%(nxtelem,),tournament=iypt2016)
            #             tplhds.append(tp[0])
            #         else:
            #             tp = TeamPlaceholder.objects.get(name="Team %d" % (placeholders[i],), tournament=iypt2016)
            #             tplhds.append(tp)
            #         print(i)
            #
            # print(tplhds)
            #
            # if parts[6]:
            #
            #     for i in range(4):
            #         stage = Stage.objects.get_or_create(order=i+1, fight=fi[0])
            #         repatt = StageAttendancePlaceholder.objects.get_or_create(stage=stage[0],team = tplhds[0], role=rep)
            #         oppatt = StageAttendancePlaceholder.objects.get_or_create(stage=stage[0],team = tplhds[1], role=opp)
            #         revatt = StageAttendancePlaceholder.objects.get_or_create(stage=stage[0],team = tplhds[2], role=rev)
            #         obsatt = StageAttendancePlaceholder.objects.get_or_create(stage=stage[0],team = tplhds[3], role=obs)
            #         tplhds = tplhds[-1:] + tplhds[:-1]
            #
            # else:
            #     for i in range(3):
            #         stage = Stage.objects.get_or_create(order=i+1, fight=fi[0])
            #         repatt = StageAttendancePlaceholder.objects.get_or_create(stage=stage[0], team=tplhds[0], role=rep)
            #         oppatt = StageAttendancePlaceholder.objects.get_or_create(stage=stage[0], team=tplhds[1], role=opp)
            #         revatt = StageAttendancePlaceholder.objects.get_or_create(stage=stage[0], team=tplhds[2], role=rev)
            #         tplhds = tplhds[-1:] + tplhds[:-1]

        elif sys.argv[1] == 'stages':


            fi = Fight.objects.get(pk=int(parts[1]))
            print(fi)

            pr=Problem.objects.get(pk=int(parts[3]))
            st = Stage.objects.get_or_create(pk=int(parts[0]), order=int(parts[2]), fight=fi,presented=pr )[0]

            team = Team.objects.get(pk=int(parts[4]))
            user = TeamMember.objects.get(attendee__active_user__user__username = parts[8])
            StageAttendance.objects.get_or_create(stage=st, team = team, role=rep, active_person=user)

            team = Team.objects.get(pk=int(parts[5]))
            user = TeamMember.objects.get(attendee__active_user__user__username=parts[9])
            StageAttendance.objects.get_or_create(stage=st, team=team, role=opp, active_person=user)

            team = Team.objects.get(pk=int(parts[6]))
            user = TeamMember.objects.get(attendee__active_user__user__username=parts[10].strip())
            StageAttendance.objects.get_or_create(stage=st, team=team, role=rev, active_person=user)

            if parts[7] != '':
                team = Team.objects.get(pk=int(parts[7]))
                StageAttendance.objects.get_or_create(stage=st, team=team, role=obs)

        elif sys.argv[1] == 'rejects':

            st = Stage.objects.get(pk=int(parts[1]))
            pr = Problem.objects.get(pk=int(parts[2]))

            if not st.rejections.filter(pk=pr.pk).exists():
                st.rejections.add(pr)

print(placeholders)