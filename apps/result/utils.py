import copy
import statistics
from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import caches

from apps.dashboard.templatetags.flags import flag_url
from apps.jury.models import GradingSheet, GroupGrade, Juror, JurorGrade
from apps.plan.models import FightRole, Round, Stage, StageAttendance
from apps.team.models import TeamMember
from apps.tournament.models import Problem


def _presented_before(team, round):

    problems = []
    for sa in StageAttendance.objects.filter(
        stage__fight__round__order__lt=round.order, team=team, role__type=FightRole.REP
    ):
        if sa.stage.presented:
            problems.append(sa.stage.presented.number)

    return sorted(problems)


def _rejected_before(team, round):

    problems = []
    for sa in StageAttendance.objects.prefetch_related("stage__rejections").filter(
        stage__fight__round__order__lt=round.order, team=team, role__type=FightRole.REP
    ):

        problems += list(sa.stage.rejections.all().values_list("number", flat=True))

    return sorted(problems)


def _opposed_before(team, round):

    problems = []
    for sa in StageAttendance.objects.filter(
        stage__fight__round__order__lt=round.order, team=team, role__type=FightRole.OPP
    ):
        if sa.stage.presented:
            problems.append(sa.stage.presented.number)

    return sorted(problems)


def _fightpreview(fight, use_cache=True):

    cpreview = caches["results"].get("preview-%s" % (fight.pk,))
    if cpreview and use_cache:
        return cpreview

    allproblems = list(
        Problem.objects.filter(tournament=fight.round.tournament).values_list(
            "number", flat=True
        )
    )
    preview = []
    for s in fight.stage_set.all():
        if fight.round.tournament.aypt_limited_problems:
            allproblems = list(
                s.rep_attendance.team.aypt_prepared_problems.all().values_list(
                    "number", flat=True
                )
            )
        sp = {"pk": s.pk}
        sp["rep"] = s.rep_attendance.team
        sp["opp"] = s.opp_attendance.team
        if fight.round.review_phase:
            sp["rev"] = s.rev_attendance.team
        sp["a"] = _rejected_before(s.rep_attendance.team, fight.round)
        sp["b"] = _presented_before(s.rep_attendance.team, fight.round)
        sp["c"] = _opposed_before(s.opp_attendance.team, fight.round)
        sp["d"] = _presented_before(s.opp_attendance.team, fight.round)
        sp["free"] = set(allproblems)
        sp["lifted"] = []
        if fight.round.tournament.aypt_limited_problems:
            sp["free"] -= set(sp["b"])
            if fight.round.tournament.oypt_multiple_oppositions:
                if len(sp["free"] - set(sp["c"])) > 0:
                    sp["free"] -= set(sp["c"])
        else:
            bans = ["a", "b", "c", "d"]
            for i in range(len(bans), 0, -1):
                banned = set([p for b in bans[:i] for p in sp[b]])
                if len(sp["free"] - banned) < 5:
                    sp["lifted"].append(bans[i - 1])
                else:
                    sp["free"] -= banned
                    break
        # augment problems with titles
        for lists in ["free", "a", "b", "c", "d"]:
            sp[lists] = list(
                Problem.objects.filter(
                    tournament=fight.round.tournament, number__in=sp[lists]
                ).values("number", "title")
            )

        # last selective
        if fight.round.preview_fixed_problem:
            sp["preview_fixed"] = True
            try:
                sp["free"] = [
                    {"number": s.presented.number, "title": s.presented.title}
                ]
            except:
                pass
        preview.append(sp)

    if use_cache:
        caches["results"].set("preview-%s" % (fight.pk,), preview, None)
    return preview


def _report_factor(stageatt):

    nr_rejected_before = len(
        _rejected_before(stageatt.team, stageatt.stage.fight.round)
    )
    nr_direct_reject = stageatt.stage.rejections.count()
    rejects = nr_direct_reject + nr_rejected_before

    max_rej = int(stageatt.stage.fight.round.tournament.allowed_rejections)
    if stageatt.stage.fight.round.type == Round.FINAL:
        return Decimal(stageatt.role.factor)
    else:
        return Decimal(stageatt.role.factor) - (
            Decimal(max(rejects - max_rej, 0)) * Decimal("0.2")
        )


def _fightresult(fight, use_cache=True):

    ccontext = caches["results"].get("points-%s" % (fight.pk,))
    if ccontext and use_cache:
        return ccontext

    teams = {}

    for stage in fight.stage_set.all():

        attendance = stage.rep_attendance_grades
        team = attendance.team
        team_id = attendance.team_id
        if attendance.grade_average:
            if team_id not in teams:
                teams[team_id] = [team, 0]
            teams[team.pk][1] += attendance.grade_average * Decimal(
                str(_report_factor(stage.rep_attendance_grades))
            )

        attendance = stage.opp_attendance_grades
        team = attendance.team
        team_id = attendance.team_id
        if attendance.grade_average:
            if team_id not in teams:
                teams[team_id] = [team, 0]
            teams[team_id][1] += attendance.grade_average * Decimal("2.0")

        if fight.round.review_phase:
            attendance = stage.rev_attendance_grades
            team = attendance.team
            team_id = attendance.team_id
            if attendance.grade_average:
                if team_id not in teams:
                    teams[team_id] = [team, 0]
                teams[team_id][1] += attendance.grade_average

    result = reversed(
        sorted(
            map(
                lambda t: {
                    "pk": t[0].pk,
                    "won": False,
                    "name": t[0].origin.name,
                    "sp": Decimal(t[1]).quantize(Decimal("1.1"), ROUND_HALF_UP),
                    "slug": t[0].origin.slug,
                },
                teams.values(),
            ),
            key=lambda t: t["sp"],
        )
    )

    result = list(result)

    highest_sp = 0
    if len(result) > 0:
        highest_sp = result[0]["sp"]

    for tidx, team in enumerate(result):
        if team["sp"] == highest_sp:
            result[tidx]["won"] = True

    context = {"room": fight.room.name, "round": fight.round.order, "result": result}

    if use_cache:
        caches["results"].set("points-%s" % (fight.pk,), context, None)
    return context


def _fightdata(fight, use_cache=True):

    ccontext = caches["results"].get("grades-%s" % (fight.pk,))
    if ccontext and use_cache:
        return ccontext

    grades_f = {}

    fight_stages = fight.stage_set.all()
    stage_info = []
    for stage in fight_stages:
        team = {}
        team["rep"] = stage.rep_attendance.team.origin.name
        team["opp"] = stage.opp_attendance.team.origin.name
        if fight.round.review_phase:
            team["rev"] = stage.rev_attendance.team.origin.name

        person = {}
        person["rep"] = ""
        person["opp"] = ""
        if fight.round.review_phase:
            person["rev"] = ""
        if stage.reporter:
            person["rep"] = stage.reporter.abbr_name
        if stage.opponent:
            person["opp"] = stage.opponent.abbr_name
        if fight.round.review_phase:
            if stage.reviewer:
                person["rev"] = stage.reviewer.abbr_name

        person["rep_name"] = ""
        person["opp_name"] = ""
        if fight.round.review_phase:
            person["rev_name"] = ""
        if stage.reporter:
            person["rep_name"] = (stage.reporter.first_name, stage.reporter.last_name)
        if stage.opponent:
            person["opp_name"] = (stage.opponent.first_name, stage.opponent.last_name)
        if fight.round.review_phase:
            if stage.reviewer:
                person["rev_name"] = (
                    stage.reviewer.first_name,
                    stage.reviewer.last_name,
                )

        avg_s = {}
        avg_s["rep"] = stage.rep_attendance.grade_average
        avg_s["opp"] = stage.opp_attendance.grade_average
        if fight.round.review_phase:
            avg_s["rev"] = stage.rev_attendance.grade_average

        factors = {}
        factors["rep"] = _report_factor(stage.rep_attendance)
        factors["opp"] = 2.0
        factors["rev"] = 1.0

        avg_w = {}
        avg_w["rep"] = stage.rep_attendance.grade_average
        if avg_w["rep"]:
            avg_w["rep"] *= Decimal(str(_report_factor(stage.rep_attendance)))
        avg_w["opp"] = stage.opp_attendance.grade_average
        if avg_w["opp"]:
            avg_w["opp"] *= Decimal("2.0")
        if fight.round.review_phase:
            avg_w["rev"] = stage.rev_attendance.grade_average

        presented = ""
        if stage.presented:
            presented = {
                "number": stage.presented.number,
                "title": stage.presented.title,
            }

        stage_info.append(
            {
                "teams": team,
                "persons": person,
                "average": avg_s,
                "w_average": avg_w,
                "factors": factors,
                "presented": presented,
                "rejections": stage.rejections.all().values("number", "title"),
            }
        )

    grades_j = []
    for jurorsess in (
        fight.jurorsession_set(manager="voting").select_related("juror").all()
    ):
        juror = jurorsess.juror
        if fight.round.tournament.publish_juror_conflicting:
            confl = [(o.name, flag_url(o)) for o in juror.conflicting.all()]
        else:
            confl = []
        grade_j = {
            "id": juror.id,
            "first_name": juror.attendee.first_name,
            "last_name": juror.attendee.last_name,
            "conflicting": confl,
        }

        grades_s = []
        for stage in fight_stages:
            grade_s = {}
            try:
                grade_s["rep"] = JurorGrade.objects.get(
                    stage_attendee=stage.rep_attendance, juror_session__juror=juror
                ).public_grade
                if (
                    fight.round.tournament.publish_partial_grades
                    and grade_s["rep"] is not None
                ):
                    par = []

                    for ggr in stage.rep_attendance.role.gradinggroup_set.all():
                        el = {
                            "value": 0,
                            "name": ggr.name,
                            "min": ggr.minimum,
                            "max": ggr.maximum,
                            "width": ggr.maximum - ggr.minimum,
                        }
                        try:
                            el["value"] = GroupGrade.objects.get(
                                stage_attendee=stage.rep_attendance,
                                juror_session__juror=juror,
                                group=ggr,
                            ).value
                        except GroupGrade.DoesNotExist:
                            pass
                        par.append(el)
                    grade_s["rep_partial"] = par
            except:
                pass
            try:
                grade_s["opp"] = JurorGrade.objects.get(
                    stage_attendee=stage.opp_attendance, juror_session__juror=juror
                ).public_grade
                if (
                    fight.round.tournament.publish_partial_grades
                    and grade_s["opp"] is not None
                ):
                    par = []

                    for ggr in stage.opp_attendance.role.gradinggroup_set.all():
                        el = {
                            "value": 0,
                            "name": ggr.name,
                            "min": ggr.minimum,
                            "max": ggr.maximum,
                            "width": ggr.maximum - ggr.minimum,
                        }
                        try:
                            el["value"] = GroupGrade.objects.get(
                                stage_attendee=stage.opp_attendance,
                                juror_session__juror=juror,
                                group=ggr,
                            ).value
                        except GroupGrade.DoesNotExist:
                            pass
                        par.append(el)
                    grade_s["opp_partial"] = par
            except:
                pass
            if fight.round.review_phase:
                try:
                    grade_s["rev"] = JurorGrade.objects.get(
                        stage_attendee=stage.rev_attendance, juror_session__juror=juror
                    ).public_grade
                except:
                    pass
            try:
                if fight.publish_partials:
                    grade_s["sheet"] = GradingSheet.objects.get(
                        jurorsession=jurorsess, stage=stage
                    )
            except:
                pass

            grades_s.append(grade_s)

        grade_j["grades"] = grades_s

        grades_j.append(grade_j)

    context = {
        "room": fight.room.name,
        "round": fight.round.order,
        "info": stage_info,
        "grades": grades_j,
    }
    if use_cache:
        caches["results"].set("grades-%s" % (fight.pk,), context, None)
    return context


def _ranking(rounds, use_cache=True, internal=False):

    if internal:
        use_cache = False

    grades = []

    grade_dicts = []

    grades_r = {}
    for round in rounds:
        if (not round.publish_ranking) and not internal:
            continue
        grades_r = copy.deepcopy(grades_r)
        for fight in round.fight_set.all():
            fightresults = _fightresult(fight, use_cache=use_cache)
            for team in fightresults["result"]:
                if team["pk"] not in grades_r:
                    grades_r[team["pk"]] = {
                        "rank": 42,
                        "pk": team["pk"],
                        "team": team["name"],
                        "slug": team["slug"],
                        "tsp": 0,
                        "sp": [],
                    }
                grades_r[team["pk"]]["sp"].append(
                    (team["sp"], team["won"], fightresults["room"])
                )
                wons = [x[1] for x in grades_r[team["pk"]]["sp"]]
                grades_r[team["pk"]]["all_won"] = all(wons) and len(wons) > 0
                grades_r[team["pk"]]["tsp"] += team["sp"]

        grlist = list(reversed(sorted(grades_r.values(), key=lambda t: t["tsp"])))
        rank = 0
        tsp = -1
        for tix, t in enumerate(grlist):
            if (t["tsp"]) != tsp:
                t["rank"] = tix + 1
                rank = tix + 1
            else:
                t["rank"] = rank
            tsp = t["tsp"]
            if len(grades) > 0:
                for op in grades[-1]:
                    if op["pk"] == t["pk"]:
                        t["rank_diff"] = op["rank"] - rank
        grades.append(grlist)

    return grades


def _jurystats(tournament, use_cache=True, emails=False):

    ccontext = caches["results"].get(
        "jurystats-%s-%d"
        % (
            emails,
            tournament.pk,
        )
    )
    if ccontext and use_cache:
        return ccontext

    jurors = []

    allgrades = []

    for juror in Juror.objects.filter(attendee__tournament=tournament):
        jgrades = []
        jbiases = []
        for js in juror.jurorsession_set.all():

            jgrinfi = []
            for gr in js.jurorgrade_set.all():
                if gr.public_grade:
                    jgrinfi.append(gr.public_grade)
                    allgrades.append(gr.public_grade)
            if len(jgrinfi) > 0:
                for stage in js.fight.stage_set.all():
                    for sa in stage.stageattendance_set.all():
                        holdupgrades = []
                        for jg in sa.jurorgrade_set.all():
                            holdupgrades.append(jg.public_grade)
                        try:
                            mygrade = sa.jurorgrade_set.get(
                                juror_session=js
                            ).public_grade
                            jbiases.append(mygrade - statistics.mean(holdupgrades))
                        except:
                            pass

            jgrades += jgrinfi

        if len(jgrades):
            data = {
                "name": juror.attendee.full_name,
                "mean": statistics.mean(jgrades),
                "stdev": statistics.stdev(jgrades),
                "activeuser": juror.attendee.active_user,
            }
            if len(jbiases):
                data["biases"] = statistics.mean(jbiases)
            if emails:
                data["email"] = juror.attendee.active_user.user.email
            jurors.append(data)

    mean = statistics.mean(allgrades)

    context = {"jurors": jurors, "mean": mean}
    if use_cache:
        caches["results"].set(
            "jurystats-%s-%d"
            % (
                emails,
                tournament.pk,
            ),
            context,
            None,
        )
    return context


def _gradedump(tournament):

    grid = []
    selectives = Round.selectives.filter(tournament=tournament)
    expl = ["Juror"]
    for round in selectives:
        for fight in round.fight_set.all():
            for stage in fight.stage_set.all():
                for sa in stage.stageattendance_set.all()[:3]:
                    expl.append(
                        "r%d-f%c-s%d-%s"
                        % (round.order, fight.room.name[-1], stage.order, sa.role.type)
                    )
    grid.append(expl)

    for juror in Juror.objects.filter(attendee__tournament=tournament):
        jurorline = [juror.attendee.full_name]
        for round in selectives:
            for fight in round.fight_set.all():
                for stage in fight.stage_set.all():
                    for sa in stage.stageattendance_set.all()[:3]:
                        try:
                            grade = sa.jurorgrade_set.get(
                                juror_session__juror=juror
                            ).public_grade
                            jurorline.append(int(grade))
                        except:
                            jurorline.append(0)
        grid.append(jurorline)

    return grid


def _resultdump(trn, use_cache=True):

    ccontext = caches["results"].get("resultdump-%d" % (trn.pk,))
    if ccontext and use_cache:
        return ccontext

    grades = []

    for round in trn.round_set.all():

        print("round:", round.order)

        round_grades = []

        for fight in round.fight_set.all().prefetch_related("room"):

            fight_grades = {"stages": [], "room": fight.room.name}
            for stage in fight.stage_set.all().prefetch_related(
                "presented", "rejections"
            ):

                stage_grades = {"rejected": [], "teams": {}}

                try:
                    stage_grades["presented"] = stage.presented.number
                except:
                    pass

                for rej in stage.rejections.all():
                    stage_grades["rejected"].append(rej.number)

                roles = [stage.rep_attendance_grades, stage.opp_attendance_grades]
                if fight.round.review_phase:
                    roles.append(stage.rev_attendance_grades)

                for att in roles:

                    stage_grades["teams"][att.role.name] = {"grades": []}
                    stage_grades["teams"][att.role.name]["team"] = att.team.origin.name
                    try:
                        stage_grades["teams"][att.role.name][
                            "person"
                        ] = att.active_person.attendee.full_name
                    except:
                        pass

                    for jur in stage.fight.jurorsession_set.all().prefetch_related(
                        "jurorgrade_set", "juror__attendee__active_user__user"
                    ):
                        try:
                            jg = jur.jurorgrade_set.get(stage_attendee=att)
                            stage_grades["teams"][att.role.name]["grades"].append(
                                [jur.juror.attendee.full_name, int(jg.grade)]
                            )
                        except Exception as e:
                            print(e)
                            pass

                fight_grades["stages"].append(stage_grades)
            round_grades.append(fight_grades)
        grades.append(round_grades)

    if use_cache:
        caches["results"].set(
            "resultdump-%d" % (trn.pk,),
            grades,
            None,
        )
    return grades


def _member_rank(trn):

    members = []
    for tm in TeamMember.students.filter(team__tournament=trn):
        member = {"perfs": [], "total": 0, "obj": tm.attendee}
        for sa in tm.stageattendance_set.all():
            member["perfs"].append(
                (
                    sa.grade_average,
                    sa.role,
                )
            )
        if len(member["perfs"]) > 0:
            member["total"] = sum([g[0] for g in member["perfs"]]) / Decimal(
                len(member["perfs"])
            )

        members.append(member)

    return sorted(members, key=lambda x: x["total"], reverse=True)


def _best_members(trn):

    members = []
    for tm in TeamMember.students.filter(team__tournament=trn):
        member = {}
        for sa in tm.stageattendance_set.all():
            if sa.role.type not in member:
                member[sa.role.type] = []
            member[sa.role.type].append(sa.grade_average)

        actives = list(member.keys())
        for k in actives:
            member["%s_tot" % k] = sum(member[k]) / Decimal(len(member[k]))

        member["obj"] = tm.attendee

        members.append(member)

    return members  # sorted(members, key=lambda x: x[""], reverse=True)
