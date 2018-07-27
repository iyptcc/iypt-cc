from django.utils import timezone

from apps.jury.models import Juror, JurorRole
from apps.registration.utils import persons_data
from apps.result.utils import _fightdata, _fightpreview, _fightresult, _ranking


def flag_context(trn):
    flags = {}
    for o in trn.origin_set.all():
        flags[o.name] = {"slug":o.slug, "alpha2":o.alpha2iso, "exists":(o.flag_pdf is not None)}
    return flags

def juryround(round):
    context = {"round_id": round.pk,
               "round": round.order}
    fis=[]
    for fight in round.fight_set.all():
        fi = {"room":fight.room.name,
              "jurors":[],
              "nonvoting":[]}

        for juroratt in fight.jurorsession_set.all():
            if juroratt.role.type == JurorRole.CHAIR:
                fi['chair'] = (juroratt.juror.attendee.first_name,juroratt.juror.attendee.last_name)
            elif juroratt.role.type == JurorRole.JUROR:
                fi['jurors'].append((juroratt.juror.attendee.first_name, juroratt.juror.attendee.last_name))
            else:
                fi['nonvoting'].append((juroratt.juror.attendee.first_name, juroratt.juror.attendee.last_name))
        fis.append(fi)

    context['free'] = []
    for j in Juror.objects.filter(attendee__tournament=round.tournament) \
        .exclude(fights__in=round.fight_set.all()) \
        .prefetch_related("attendee__active_user__user"):
        context['free'].append((j.attendee.first_name, j.attendee.last_name))

    context["fights"]=fis

    return context

def problem_select(round):

    teams = []
    for fi in round.fight_set.all():
        teams+=list(fi.stage_set.first().attendees.all().values_list("origin__name",flat=True))

    problems = [(p.number,p.title) for p in round.tournament.problem_set.all()]

    context = {}
    context["teams"] = teams
    context["problems"] = problems
    context["round"] = round.order

    print(context)
    return context

def teamround(round):
    context = {"round_id": round.pk,
               "round": round.order}
    fis=[]
    for fight in round.fight_set.all():
        stage = fight.stage_set.first()
        fi = {"room":fight.room.name,
              "reporter":stage.rep_attendance.team.origin.name,
              "opponent":stage.opp_attendance.team.origin.name,
              "reviewer":stage.rev_attendance.team.origin.name,
              }
        if stage.obs_attendance:
            fi["observer"]=stage.obs_attendance.team.origin.name

        fis.append(fi)

    context["fights"]=fis

    return context

def ranking(round):
    rounds = round.tournament.round_set(manager="selectives").all()
    grades = _ranking(rounds)
    if len(grades)>=round.order:
        return {"round": round.order, "ranks": grades[round.order-1]}
    else:
        return {"round":round.order, "ranks":[]}

def juryfeedback(fight):
    context = {"fight_id": fight.pk,
               "round": fight.round.order,
               "room": fight.room.name}

    context["teams"] = list(fight.stage_set.first().attendees.all().values_list("origin__name",flat=True))

    chair = fight.jurorsession_set(manager="chair").first()
    context["chair"] = {"firstname":chair.juror.attendee.first_name, "lastname":chair.juror.attendee.last_name}

    jurors = fight.jurorsession_set(manager="jurors").all()
    context["jurors"] = []
    for j in jurors:
        context["jurors"].append({"fistname":j.juror.attendee.first_name,"lastname":j.juror.attendee.last_name})

    return context

def preview(fight):

    context = {"fight_id": fight.pk,
               "round": fight.round.order,
               "room": fight.room.name}

    prblms = []
    for problem in fight.round.tournament.problem_set.all():
        prblms.append((problem.number, problem.title))

    context["problems"] = prblms

    stages = []

    for idx, stage in enumerate(_fightpreview(fight)):
        sd = {"order":idx+1,
              "reporter":stage["rep"].origin.name,
              "opponent":stage["opp"].origin.name,
              "reviewer":stage["rev"].origin.name,
              "problems":list(stage['free']),
              "rejected_reporter":stage["a"],
              "presented_reporter":stage["b"],
              "opposed_opponent":stage["c"],
              "presented_opponent":stage["d"],
              "lifted_bans":stage["lifted"]}
        stages.append(sd)

    context["stages"]=stages

    return context

def result(fight):

    context = {"fight_id": fight.pk,
               "round": fight.round.order,
               "room": fight.room.name}

    fightinfo = _fightdata(fight, use_cache=False)
    context["stages"] = []
    context["average"] = []
    context["factor"] = []
    context["points"] = []
    
    results = _fightresult(fight,False)["result"]
    context["ranking"] = [{'team':t["name"],"points":t["sp"]} for t in results]


    for idx, stage in enumerate(fightinfo["info"]):
        context["stages"].append({
            "order":idx+1,
            "reporter_team":stage["teams"]["rep"],
            "opponent_team":stage["teams"]["opp"],
            "reviewer_team":stage["teams"]["rev"],
            "reporter_person_lastname": stage["persons"]["rep_name"][1],
            "reporter_person_firstname": stage["persons"]["rep_name"][0],
            "opponent_person_lastname": stage["persons"]["opp_name"][1],
            "opponent_person_firstname": stage["persons"]["opp_name"][0],
            "reviewer_person_lastname": stage["persons"]["rev_name"][1],
            "reviewer_person_firstname": stage["persons"]["rev_name"][0],
            "presented":(stage["presented"],"FIXME"), # FIXME in utils
            "rejected":[(n,"FIXME") for n in stage['rejections']],
        })

        context["average"].append({
            "reporter":stage["average"]["rep"],
            "opponent":stage["average"]["opp"],
            "reviewer":stage["average"]["rev"],
        })

        context["factor"].append({
            "reporter":stage["factors"]["rep"],
            "opponent":stage["factors"]["opp"],
            "reviewer":stage["factors"]["rev"],
        })

        context["points"].append({
            "reporter":stage["w_average"]["rep"],
            "opponent":stage["w_average"]["opp"],
            "reviewer":stage["w_average"]["rev"],
        })

    context["jurors"] = []
    for juror in fightinfo["grades"]:
        j = {
             "firstname": juror["first_name"],
             "lastname": juror["last_name"]
        }
        stages = []
        for stage in juror["grades"]:
            stages.append({
                "reporter":stage["rep"],
                "opponent":stage["opp"],
                "reviewer":stage["rev"],
            })
        j["stages"] = stages

        context["jurors"].append(j)

    return context

def persons(persons):
    pers = []
    for att in persons.prefetch_related("active_user__user","team_set__origin"):
        pers.append({
            "first_name":att.first_name,
         "last_name":att.last_name,
         "email":att.active_user.user.email,
         "team":list(att.team_set.all().values_list("origin__name",flat=True))
         })
    context={"persons":pers}
    return context

def registration(persons):

    pers = []
    atts, aps = persons_data(persons,hidden=True)

    for att in persons.prefetch_related("active_user__user", "team_set__origin"):
        p = {"first_name": att.first_name,
             "last_name": att.last_name,
             "email": att.active_user.user.email,
             "team": list(att.teammember_set.all().values_list("team__origin__name","role__name")),
             "roles":list(att.roles.all().values_list("name", flat=True)),
             }
        p["data"] = atts[att.id]["data"]
        pers.append(p)

    context = {"persons": pers,"properties":aps, "flags":flag_context(persons[0].tournament)}
    return context

def invoice(account, attendee):
    payments = account.outgoing_payments.filter(aborted_at__isnull=True, cleared_at__isnull=True)
    ps = []
    total = 0
    for po in payments:
        due = po.due_at
        if due == None:
            due = timezone.now()
        elif due < timezone.now():
            due = timezone.now()
        ps.append({"due":due.strftime('%b %d, %Y'), "amount":po.amount, "reference":po.reference})
        total += po.amount
    print(ps)
    context = {"receiver_address":payments[0].receiver.address, "sender_address":account.address,'payments':ps, "total":total,"requester":attendee.full_name}
    return context
