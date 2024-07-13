import copy
import random

from celery import current_task, shared_task

from apps.jury.models import Juror
from apps.tournament.models import Tournament

from .utils import check_conflict_origin, plan_cost


def assignAneal(
    tournament_id,
    total_rounds=1000,
    room_jurors=5,
    cooling_base=0.99,
    fix_rounds=0,
    task=None,
):

    error = []

    def _copy(plan):
        nplan = []

        for round in plan:

            nround = {"fights": [], "free": copy.copy(round["free"])}

            for fight in round["fights"]:
                nfight = {
                    "fight": fight["fight"],
                    "jurors": copy.copy(fight["jurors"]),
                    "nonvoting": copy.copy(fight["nonvoting"]),
                }

                nround["fights"].append(nfight)

            nplan.append(nround)

        return nplan

    def _swap(plan, fix_rounds):

        def random_round(plan, fix_rounds):
            return random.randint(fix_rounds, len(plan) - 1)

        def random_juror(plan, round_n):

            ret = {}

            _round_n = round_n
            ret["round_n"] = _round_n

            _jurors = (
                len(plan[_round_n]["free"])
                + len(plan[_round_n]["fights"]) * room_jurors
            )

            _juror_n = random.randint(0, _jurors - 1)

            if _juror_n < len(plan[_round_n]["free"]):
                _juror = plan[_round_n]["free"][_juror_n]
                ret["free"] = True
            else:
                _juror_n -= len(plan[_round_n]["free"])

                _fight_n = _juror_n // room_jurors

                ret["fight"] = plan[_round_n]["fights"][_fight_n]["fight"]
                ret["fight_n"] = _fight_n

                _juror = plan[_round_n]["fights"][_fight_n]["jurors"][
                    (_juror_n % room_jurors)
                ]
                ret["juror_n"] = _juror_n % room_jurors

            ret["juror"] = _juror

            return ret

        def check_hard(plan, src, dst):

            # from free to free
            if "free" in dst and "free" in src:
                return True

            def check_chair_in_fight(fight):
                return any([j.possible_chair for j in fight["jurors"]])

            def check_fight_local(src, dst):
                # check conflict in fight
                if "fight" in src:
                    if check_conflict_origin(src["fight"], dst["juror"]):
                        return True
                    if not check_chair_in_fight(
                        plan[src["round_n"]]["fights"][src["fight_n"]]
                    ):
                        return True

            if check_fight_local(src, dst) or check_fight_local(dst, src):
                return False

            # team and chair meet often
            def meet_often(fight, juror):
                if (
                    list(filter(lambda j: j.possible_chair, fight["jurors"]))[0]
                    != juror
                ):
                    return False

                this_origins = set(
                    fight["fight"]
                    .stage_set.get(order=1)
                    .attendees.all()
                    .values_list("origin_id", flat=True)
                )

                meets = 1
                for round in plan:
                    for f in round["fights"]:
                        fi_chairs = list(
                            filter(lambda j: j.possible_chair, f["jurors"])
                        )
                        if len(fi_chairs) > 0 and fi_chairs[0] == juror:
                            # is chair
                            fight_origins = set(
                                f["fight"]
                                .stage_set.get(order=1)
                                .attendees.all()
                                .values_list("origin_id", flat=True)
                            )
                            if len(this_origins & fight_origins) != 0:
                                meets += 1

                if meets > 2:
                    return True

            if "free" not in src:
                if meet_often(
                    plan[src["round_n"]]["fights"][src["fight_n"]], dst["juror"]
                ):
                    return False
            if "free" not in dst:
                if meet_often(
                    plan[dst["round_n"]]["fights"][dst["fight_n"]], src["juror"]
                ):
                    return False

            # availability
            # at most once per round

            return True

        def switch_juror(plan, src, dst):
            # delete juror from src
            if "free" in dst:
                plan[dst["round_n"]]["free"].remove(dst["juror"])
                plan[dst["round_n"]]["free"].append(src["juror"])
            else:
                plan[dst["round_n"]]["fights"][dst["fight_n"]]["jurors"].remove(
                    dst["juror"]
                )
                plan[dst["round_n"]]["fights"][dst["fight_n"]]["jurors"].append(
                    src["juror"]
                )

            return plan

        swround = random_round(plan, fix_rounds)
        src = random_juror(plan, swround)
        dst = random_juror(plan, swround)

        tmplan = _copy(plan)

        tmplan = switch_juror(tmplan, src, dst)
        tmplan = switch_juror(tmplan, dst, src)

        while not (check_hard(tmplan, src, dst)):
            swround = random_round(plan, fix_rounds)
            src = random_juror(plan, swround)
            dst = random_juror(plan, swround)

            tmplan = _copy(plan)

            tmplan = switch_juror(tmplan, src, dst)
            tmplan = switch_juror(tmplan, dst, src)

            # print("check new random")

        return tmplan

    def _initial(trn, chairs_qs, jurors_qs, fix_rounds):
        """
        tries to create initital plan straight forward.

        :param trn: tournament
        :param chairs_qs: chairs queryset
        :param jurors_qs: jurors queryset
        :return: (valid, plan)
        """
        plan = []

        valid_plan = True

        chair_meets = {}

        non_voted = []

        print("create initial schedule")
        for round in trn.round_set(manager="selectives").all():

            if round.order <= fix_rounds:
                round_fights = {"fights": [], "free": []}

                for fight in round.fight_set.all():
                    fight_data = {"fight": fight, "jurors": [], "nonvoting": []}

                    fight_data["jurors"] = [
                        js.juror
                        for js in list(fight.jurorsession_set(manager="voting").all())
                    ]
                    fight_data["nonvoting"] = [
                        js.juror
                        for js in list(
                            fight.jurorsession_set(manager="nonvoting").all()
                        )
                    ]

                    chair = fight.jurorsession_set(manager="chair").first().juror

                    participant_origins = set(
                        fight.stage_set.get(order=1)
                        .attendees.all()
                        .values_list("origin_id", flat=True)
                    )

                    if chair not in chair_meets:
                        chair_meets[chair] = {}
                    for ori in list(participant_origins):
                        if ori not in chair_meets[chair]:
                            chair_meets[chair][ori] = 1
                        else:
                            chair_meets[chair][ori] += 1

                    non_voted = list(set(fight_data["nonvoting"]) | set(non_voted))

                    round_fights["fights"].append(fight_data)

            else:
                # part of plan
                round_fights = {"fights": []}
                # keep track of already assign jurors in this round (no double assignments)
                assigned_jurors = []

                chairs = list(chairs_qs.filter(availability=round))

                # if len(plan) == 0:
                # no inexperienced in first round
                jurors = list(
                    jurors_qs.filter(
                        availability=round, experience__gte=Juror.EXPERIENCE_LOW
                    )
                )

                # jurors+=non_voted

                new_jurors_cur = list(
                    jurors_qs.filter(
                        availability=round, experience=Juror.EXPERIENCE_NEW
                    )
                )

                new_jurors = []
                for j in new_jurors_cur:
                    if j in non_voted:
                        jurors.append(j)
                    else:
                        new_jurors.append(j)

                # else:
                # limit to available jurors
                # HARD: absentJuror
                # jurors = list(jurors_qs.filter(availability=round))

                # mix for more uniform plan
                random.shuffle(chairs)
                random.shuffle(jurors)

                for fight in round.fight_set.all():
                    fight_data = {"fight": fight, "jurors": [], "nonvoting": []}

                    # get origins from teams
                    participant_origins = set(
                        fight.stage_set.get(order=1)
                        .attendees.all()
                        .values_list("origin_id", flat=True)
                    )

                    # find a chair
                    meetthrice = {}
                    for chair in chairs:
                        conflicting = set(
                            chair.conflicting.all().values_list("id", flat=True)
                        )

                        possible = True
                        if chair in chair_meets:
                            for ori in list(participant_origins):
                                if (
                                    ori in chair_meets[chair]
                                    and chair_meets[chair][ori]
                                    > trn.jury_chair_maximum_meet_origin
                                ):
                                    possible = False
                                    meetthrice[chair] = ori

                        if (
                            len(participant_origins & conflicting) == 0
                            and chair not in assigned_jurors
                            and possible
                        ):
                            # check only twice:

                            fight_data["jurors"].append(chair)
                            assigned_jurors.append(chair)
                            if chair not in chair_meets:
                                chair_meets[chair] = {}
                            for ori in list(participant_origins):
                                if ori not in chair_meets[chair]:
                                    chair_meets[chair][ori] = 1
                                else:
                                    chair_meets[chair][ori] += 1
                            break

                    # if none found: invalid plan
                    # HARD: emptySeat
                    if len(fight_data["jurors"]) < 1:
                        valid_plan = False
                        error.append(
                            f"""
                        No chair for fight {fight} found: 
                        we already assigned: {assigned_jurors}
                        meet team too often: {meetthrice}
                         """
                        )

                    round_fights["fights"].append(fight_data)

                for fi, fight in enumerate(round.fight_set.all()):

                    fight_data = round_fights["fights"][fi]
                    participant_origins = set(
                        fight.stage_set.get(order=1)
                        .attendees.all()
                        .values_list("origin_id", flat=True)
                    )

                    # find the jurors
                    for i in range(room_jurors - 1):
                        for juror in jurors:
                            conflicting = set(
                                juror.conflicting.all().values_list("id", flat=True)
                            )
                            if (
                                len(participant_origins & conflicting) == 0
                                and juror not in assigned_jurors
                            ):
                                fight_data["jurors"].append(juror)
                                assigned_jurors.append(juror)
                                break

                    # if not enough jurors found
                    # HARD: emptySeat
                    if len(fight_data["jurors"]) < room_jurors:
                        valid_plan = False
                        error.append(
                            f"""
                        Not {room_jurors-1} Jurors for fight {fight} found
                        only found: {fight_data['jurors']}
                        we already assigned: {assigned_jurors}
                        """
                        )

                    # assign nonvoting
                    for i in range(3):
                        for juror in new_jurors:
                            conflicting = set(
                                juror.conflicting.all().values_list("id", flat=True)
                            )
                            if (
                                len(participant_origins & conflicting) == 0
                                and juror not in non_voted
                            ):
                                fight_data["nonvoting"].append(juror)
                                non_voted.append(juror)
                                break

                round_fights["free"] = list(set(jurors) - set(assigned_jurors))
            plan.append(round_fights)

        print("found valid plan: %s" % valid_plan)
        return (valid_plan, plan, error)

    # get tournament from id
    trn = Tournament.objects.get(pk=tournament_id)

    # get chairs and all jurors
    chairs_qs = Juror.objects.filter(
        attendee__tournament_id=trn.id, possible_chair=True
    )
    jurors_qs = Juror.objects.filter(attendee__tournament_id=trn.id)

    # make jurors
    chairs = list(chairs_qs)
    jurors = list(jurors_qs)

    # check if valid plan is possible at all
    found_valid = False
    plan = []
    errors = []
    for i in range(10):
        valid_plan, plan, errors = _initial(trn, chairs_qs, jurors_qs, fix_rounds)
        if valid_plan:
            found_valid = True
            break

    if not found_valid:
        return ([], errors)

        # raise Exception("no valid initial plan found after 3 tries")

    # calculate costs of plan
    cost = plan_cost(plan, jurors)["total"]
    best_plan = _copy(plan)
    best_cost = cost

    # total_rounds = 2000
    # cooling_base = 0.99

    cost_obj = {}

    cost_graph = {}
    best_cost_graph = []
    for i in range(total_rounds):

        if task:
            if i % 500 == 0:
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i,
                        "total": total_rounds,
                        "costs": cost_graph,
                        "best_costs": best_cost_graph,
                    },
                )
        else:
            if i % 500 == 0:
                print("%d %% -> %f" % ((100 * i) // total_rounds, best_cost))

        new_plan = _swap(plan, fix_rounds)
        new_cost_full = plan_cost(new_plan, jurors)
        new_cost = new_cost_full["total"]

        for key in new_cost_full:
            if key not in cost_graph:
                cost_graph[key] = [new_cost_full[key]]
            else:
                cost_graph[key].append(new_cost_full[key])
        best_cost_graph.append(best_cost)

        if new_cost < cost or random.random() < (cooling_base**i):
            cost = new_cost
            plan = new_plan

        if new_cost < best_cost:
            best_cost = new_cost
            best_plan = _copy(new_plan)

            # print("min cost: %f , act cost: %f"%(best_cost, cost))

    # pprint.pprint(best_plan)

    cost_obj["best_cost"] = best_cost
    cost_obj["best_cost_graph"] = best_cost_graph
    cost_obj["cost_graph"] = cost_graph

    return (best_plan, cost_obj)
