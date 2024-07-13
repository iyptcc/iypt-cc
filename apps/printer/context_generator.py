from django.core.signing import Signer
from django.urls import reverse
from django.utils import timezone

from apps.jury.models import Juror, JurorRole
from apps.plan.models import Fight, FightRole, Round, Stage
from apps.registration.utils import persons_data
from apps.result.utils import _fightdata, _fightpreview, _fightresult, _ranking
from apps.team.models import Team, TeamMember, TeamRole


def flag_context(trn):
    flags = {}
    for o in trn.origin_set.all():
        flags[o.name] = {
            "slug": o.slug,
            "alpha2": o.alpha2iso,
            "exists": bool(o.flag_pdf),
        }
    return flags


def juryround(round):
    context = {
        "round_id": round.pk,
        "round": round.order,
        "flags": flag_context(round.tournament),
    }
    fis = []
    for fight in round.fight_set.all():
        fi = {"room": fight.room.name, "jurors": [], "nonvoting": []}

        stage = fight.stage_set.first()
        fi = {
            **fi,
            "reporter": stage.rep_attendance.team.origin.name,
            "opponent": stage.opp_attendance.team.origin.name,
            "reviewer": stage.rev_attendance.team.origin.name,
        }
        if stage.obs_attendance:
            fi["observer"] = stage.obs_attendance.team.origin.name

        for juroratt in fight.jurorsession_set.all():
            if juroratt.role.type == JurorRole.CHAIR:
                fi["chair"] = (
                    juroratt.juror.attendee.first_name,
                    juroratt.juror.attendee.last_name,
                )
            elif juroratt.role.type == JurorRole.JUROR:
                fi["jurors"].append(
                    (
                        juroratt.juror.attendee.first_name,
                        juroratt.juror.attendee.last_name,
                    )
                )
            else:
                fi["nonvoting"].append(
                    (
                        juroratt.juror.attendee.first_name,
                        juroratt.juror.attendee.last_name,
                    )
                )
        fis.append(fi)

    context["free"] = []
    for j in (
        Juror.objects.filter(attendee__tournament=round.tournament)
        .exclude(fights__in=round.fight_set.all())
        .exclude(round=round)
        .prefetch_related("attendee__active_user__user")
    ):
        context["free"].append((j.attendee.first_name, j.attendee.last_name))

    context["reserve"] = []
    for j in round.reserved_jurors.all().prefetch_related(
        "attendee__active_user__user"
    ):
        context["reserve"].append((j.attendee.first_name, j.attendee.last_name))
    context["fights"] = fis

    return context


def problem_select(round):

    teams = []
    for fi in round.fight_set.all():
        teams += list(
            fi.stage_set.first().attendees.all().values_list("origin__name", flat=True)
        )

    problems = [(p.number, p.title) for p in round.tournament.problem_set.all()]

    context = {}
    context["teams"] = teams
    context["problems"] = problems
    context["round"] = round.order

    print(context)
    return context


def teamround(round):
    context = {
        "round_id": round.pk,
        "round": round.order,
        "flags": flag_context(round.tournament),
    }
    fis = []
    for fight in round.fight_set.all():
        stage = fight.stage_set.first()
        fi = {
            "room": fight.room.name,
            "reporter": stage.rep_attendance.team.origin.name,
            "opponent": stage.opp_attendance.team.origin.name,
            "reviewer": stage.rev_attendance.team.origin.name,
        }
        if stage.obs_attendance:
            fi["observer"] = stage.obs_attendance.team.origin.name

        fis.append(fi)

    context["fights"] = fis

    return context


def ranking(round):
    rounds = round.tournament.round_set(manager="selectives").all()
    grades = _ranking(rounds)
    # "team": [("Austria", "Team Leader"), ("Brazil", "Member"), ],

    if len(grades) >= round.order:
        ranks = grades[round.order - 1]
        for team in ranks:
            t = Team.objects.get(pk=team["pk"], tournament=round.tournament)
            team["members"] = []
            for tm in t.teammember_set.all():
                tmd = {
                    "role": tm.role.name,
                    "first_name": tm.attendee.first_name,
                    "last_name": tm.attendee.last_name,
                }
                team["members"].append(tmd)
        return {
            "round": round.order,
            "ranks": ranks,
            "flags": flag_context(round.tournament),
        }
    else:
        return {"round": round.order, "ranks": [], "flags": []}


def juryfeedback(baseurl, fight):
    context = {
        "fight_id": fight.pk,
        "round": fight.round.order,
        "room": fight.room.name,
    }

    signer = Signer()

    context["teams"] = [
        {"name": att.origin.name, "signed_id": signer.sign("sa%05d" % (att.id))}
        for att in fight.stage_set.first().attendees.all()
    ]

    chair = fight.jurorsession_set(manager="chair").first()
    context["chair"] = {
        "first_name": chair.juror.attendee.first_name,
        "last_name": chair.juror.attendee.last_name,
    }

    jurors = fight.jurorsession_set(manager="jurors").all()
    context["jurors"] = []
    for j in jurors:
        context["jurors"].append(
            {
                "first_name": j.juror.attendee.first_name,
                "last_name": j.juror.attendee.last_name,
            }
        )
    context["links"] = [
        "%s%s"
        % (
            baseurl,
            reverse(
                "feedback:edit",
                kwargs={"fight_id": fight.id, "t_slug": team.origin.slug},
            ),
        )
        for team in fight.stage_set.first().attendees.all()
    ]
    return context


def jurygrading(stage):
    context = {
        "fight_id": stage.fight.pk,
        "round": stage.fight.round.order,
        "room": stage.fight.room.name,
        "stage": stage.order,
    }

    context["reporter"] = stage.rep_attendance.team.origin.name
    context["opponent"] = stage.opp_attendance.team.origin.name
    context["reviewer"] = stage.rev_attendance.team.origin.name

    signer = Signer()

    chair = stage.fight.jurorsession_set(manager="chair").first()
    context["chair"] = {
        "first_name": chair.juror.attendee.first_name,
        "last_name": chair.juror.attendee.last_name,
        "signed_id": signer.sign("js%05d_%d" % (chair.id, stage.order)),
    }

    jurors = stage.fight.jurorsession_set(manager="jurors").all()
    context["jurors"] = []
    for j in jurors:
        print(j.id)
        context["jurors"].append(
            {
                "first_name": j.juror.attendee.first_name,
                "last_name": j.juror.attendee.last_name,
                "signed_id": signer.sign("js%05d_%d" % (j.id, stage.order)),
            }
        )

    nvs = stage.fight.jurorsession_set(manager="nonvoting").all()
    context["nonvoting"] = []
    for j in nvs:
        print(j.id)
        context["nonvoting"].append(
            {
                "first_name": j.juror.attendee.first_name,
                "last_name": j.juror.attendee.last_name,
                "signed_id": signer.sign("js%05d_%d" % (j.id, stage.order)),
            }
        )

    return context


def preview(fight):

    context = {
        "fight_id": fight.pk,
        "round": fight.round.order,
        "room": fight.room.name,
    }

    prblms = []
    for problem in fight.round.tournament.problem_set.all():
        prblms.append((problem.number, problem.title))

    context["problems"] = prblms

    stages = []

    for idx, stage in enumerate(_fightpreview(fight)):
        sd = {
            "order": idx + 1,
            "reporter": stage["rep"].origin.name,
            "opponent": stage["opp"].origin.name,
            "reviewer": stage["rev"].origin.name,
            "problems": [pr["number"] for pr in list(stage["free"])],
            "rejected_reporter": [pr["number"] for pr in stage["a"]],
            "presented_reporter": [pr["number"] for pr in stage["b"]],
            "opposed_opponent": [pr["number"] for pr in stage["c"]],
            "presented_opponent": [pr["number"] for pr in stage["d"]],
            "lifted_bans": stage["lifted"],
        }
        stages.append(sd)

    context["stages"] = stages

    return context


def gradeoverview(fight: Fight):
    signer = Signer()
    context = {
        "fight_id": fight.pk,
        "signed_id": signer.sign("fi%05d" % (fight.id)),
        "round": fight.round.order,
        "room": fight.room.name,
    }

    prblms = []
    for problem in fight.round.tournament.problem_set.all():
        prblms.append((problem.number, problem.title))

    context["problems"] = prblms

    stages = []

    for idx, stage in enumerate(_fightpreview(fight)):
        sd = {
            "order": idx + 1,
            "rep": {"name": stage["rep"].origin.name},
            "opp": {"name": stage["opp"].origin.name},
            "rev": {"name": stage["rev"].origin.name},
            "problems": [pr["number"] for pr in list(stage["free"])],
            "rejected_reporter": [pr["number"] for pr in stage["a"]],
            "presented_reporter": [pr["number"] for pr in stage["b"]],
            "opposed_opponent": [pr["number"] for pr in stage["c"]],
            "presented_opponent": [pr["number"] for pr in stage["d"]],
            "lifted_bans": stage["lifted"],
        }

        st = Stage.objects.get(pk=stage["pk"])
        for att in st.stageattendance_set.all():
            if att.role.type not in sd:
                continue
            tms = att.team.teammember_set.filter(
                role__type__in=[TeamRole.CAPTAIN, TeamRole.MEMBER]
            )
            m: TeamMember
            sd[att.role.type]["members"] = []
            for m in tms:
                sd[att.role.type]["members"].append(
                    {
                        "first_name": m.attendee.first_name,
                        "last_name": m.attendee.last_name,
                        "presented": list(
                            m.stageattendance_set.filter(role__type=FightRole.REP)
                            .all()
                            .values_list("stage__presented__number", flat=True)
                        ),
                    }
                )
        stages.append(sd)

    print(stages)
    person_lines = [
        [[None, None, None] for j in range(len(stages))]
        for i in range(
            max([len(sd[r]["members"]) for sd in stages for r in ["rep", "opp", "rev"]])
        )
    ]
    for sid, sd in enumerate(stages):
        for rid, r in enumerate(["rep", "opp", "rev"]):
            for mid, m in enumerate(sd[r]["members"]):
                person_lines[mid][sid][rid] = m
    context["stages"] = stages
    context["person_lines"] = person_lines

    chair = fight.jurorsession_set(manager="chair").first()
    context["chair"] = {
        "first_name": chair.juror.attendee.first_name,
        "last_name": chair.juror.attendee.last_name,
    }

    jurors = fight.jurorsession_set(manager="jurors").all()
    context["jurors"] = []
    for j in jurors:
        context["jurors"].append(
            {
                "first_name": j.juror.attendee.first_name,
                "last_name": j.juror.attendee.last_name,
            }
        )

    nvs = fight.jurorsession_set(manager="jurors").all()
    context["nonvoting"] = []
    for j in nvs:
        context["nonvoting"].append(
            {
                "first_name": j.juror.attendee.first_name,
                "last_name": j.juror.attendee.last_name,
            }
        )

    context["assistants"] = [
        {"first_name": o.first_name, "last_name": o.last_name}
        for o in fight.operators.all()
    ]

    context["flags"] = flag_context(fight.round.tournament)
    return context


def result(fight):

    context = {
        "fight_id": fight.pk,
        "round": fight.round.order,
        "room": fight.room.name,
    }

    fightinfo = _fightdata(fight, use_cache=False)
    context["stages"] = []
    context["average"] = []
    context["factor"] = []
    context["points"] = []

    results = _fightresult(fight, False)["result"]
    context["ranking"] = [{"team": t["name"], "points": t["sp"]} for t in results]

    for idx, stage in enumerate(fightinfo["info"]):
        cxs = {
            "order": idx + 1,
            "reporter_team": stage["teams"]["rep"],
            "opponent_team": stage["teams"]["opp"],
            "reporter_person_last_name": stage["persons"]["rep_name"][1],
            "reporter_person_first_name": stage["persons"]["rep_name"][0],
            "opponent_person_last_name": stage["persons"]["opp_name"][1],
            "opponent_person_first_name": stage["persons"]["opp_name"][0],
            "presented": (stage["presented"], "FIXME"),  # FIXME in utils
            "rejected": [(n, "FIXME") for n in stage["rejections"]],
        }
        cxa = {
            "reporter": stage["average"]["rep"],
            "opponent": stage["average"]["opp"],
        }
        cxf = {
            "reporter": stage["factors"]["rep"],
            "opponent": stage["factors"]["opp"],
        }
        cxp = {
            "reporter": stage["w_average"]["rep"],
            "opponent": stage["w_average"]["opp"],
        }
        if fight.round.review_phase:
            cxs["reviewer_team"] = stage["teams"]["rev"]
            cxs["reviewer_person_last_name"] = stage["persons"]["rev_name"][1]
            cxs["reviewer_person_first_name"] = stage["persons"]["rev_name"][0]

            cxa["reviewer"] = stage["average"]["rev"]

            cxf["reviewer"] = stage["factors"]["rev"]

            cxp["reviewer"] = stage["w_average"]["rev"]

        context["stages"].append(cxs)
        context["average"].append(cxa)
        context["factor"].append(cxf)
        context["points"].append(cxp)

    context["jurors"] = []
    for juror in fightinfo["grades"]:
        j = {"first_name": juror["first_name"], "last_name": juror["last_name"]}
        stages = []
        for stage in juror["grades"]:
            cxstage = {
                "reporter": stage["rep"],
                "opponent": stage["opp"],
            }
            if fight.round.review_phase:
                cxstage["reviewer"] = stage["rev"]
            stages.append(cxstage)

        j["stages"] = stages

        context["jurors"].append(j)

    return context


def persons(persons):
    pers = []
    for att in persons.prefetch_related("active_user__user", "team_set__origin"):
        pers.append(
            {
                "first_name": att.first_name,
                "last_name": att.last_name,
                "email": att.active_user.user.email,
                "team": list(att.team_set.all().values_list("origin__name", flat=True)),
            }
        )
    context = {"persons": pers, "flags": flag_context(persons.first().tournament)}
    return context


def teams(ts):
    trn = ts.first().tournament
    rounds = trn.round_set(manager="selectives").all()
    grades = _ranking(rounds)
    # "team": [("Austria", "Team Leader"), ("Brazil", "Member"), ],

    ranks = None
    if len(grades) > 0:
        ranks = grades[-1]

    alphabet = []
    teams = {}
    for team in ts:
        t = {"origin": team.origin.name}
        for role in [TeamRole.CAPTAIN, TeamRole.MEMBER, TeamRole.LEADER]:
            tms = team.teammember_set.filter(role__type=role)
            t[role] = []
            m: TeamMember
            for m in tms:
                t[role].append(
                    {
                        "first_name": m.attendee.first_name,
                        "last_name": m.attendee.last_name,
                        "presented": list(
                            m.stageattendance_set.filter(role__type=FightRole.REP)
                            .all()
                            .values_list("stage__presented__number", flat=True)
                        ),
                    }
                )
        alphabet.append(team.origin.name)
        teams[team.origin.name] = t

    final_rank = None
    final = Round.finals.filter(tournament=trn)
    if final.exists():
        finalfight = final.first().fight_set.first()
        if finalfight is not None:
            final_rank = _fightresult(finalfight, use_cache=False)["result"]
    context = {
        "teams": teams,
        "ranks": ranks,
        "alphabetical": alphabet,
        "final": final_rank,
        "flags": flag_context(ts.first().tournament),
    }
    return context


def registration(persons):

    pers = []
    atts, aps = persons_data(persons, hidden=True)

    for att in persons.prefetch_related("active_user__user", "team_set__origin"):
        p = {
            "first_name": att.first_name,
            "last_name": att.last_name,
            "email": att.active_user.user.email,
            "team": list(
                att.teammember_set.all().values_list("team__origin__name", "role__name")
            ),
            "roles": list(att.roles.all().values_list("name", flat=True)),
        }
        p["data"] = atts[att.id]["data"]
        pers.append(p)

    context = {
        "persons": pers,
        "properties": aps,
        "flags": flag_context(persons[0].tournament),
    }
    return context


def invoice(account, attendee):
    payments = account.outgoing_payments.filter(
        aborted_at__isnull=True, cleared_at__isnull=True
    )
    ps = []
    total = 0
    for po in payments:
        due = po.due_at
        if due == None:
            due = timezone.now()
        elif due < timezone.now():
            due = timezone.now()
        ps.append(
            {
                "due": due.strftime("%b %d, %Y"),
                "amount": po.amount,
                "reference": po.reference,
            }
        )
        total += po.amount
    print(ps)
    context = {
        "receiver_address": payments[0].receiver.address,
        "sender_address": account.address,
        "payments": ps,
        "total": total,
        "requester": attendee.full_name,
    }
    return context
