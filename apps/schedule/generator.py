import copy
import math
import random


def _cost(plan):

    meet, team_rooms, equal_rows, startrole = cal_stats(plan)
    teamnr = len(meet)
    optimal4fights = ((teamnr % 3) * 4 / teamnr) * len(plan)
    # print("optimal nr: %f"%optimal4fights)

    cost4 = 0
    consec4 = 0
    for team in range(teamnr):
        rooms = [tr[team] for tr in team_rooms]
        rounds = []
        for r in rooms:
            if r:
                ro = r.split(" - ")
                rounds.append(int(ro[0]))
        rounds = sorted(rounds)
        for ri in range(len(rounds) - 1):
            if rounds[ri + 1] - rounds[ri] < 2:
                consec4 += 1

        room4 = sum(map(bool, rooms))
        # print("rooms")
        # print(rooms)
        if room4 < math.floor(optimal4fights) or room4 > math.ceil(optimal4fights):
            cost4 += 1

    costmeet = 0
    for team1 in meet:
        for team2 in team1:
            if len(team2) > 1:
                costmeet += (len(team2) - 1) ** 4

    # costrole = 0
    # for team in startrole:
    #    for role in team:
    #        if role > 2:
    #            costrole += role**4

    # print("4er: %f , meet: %d, role:%d, consec4: %d"%(cost4, costmeet,consec4))
    return {
        "no-4": cost4,
        "meet": costmeet,
        "consec-4": consec4,
        "total": cost4 + costmeet + consec4,
    }


def generate_plan(teams, rounds, simulation_rounds):

    def _copy(plan):
        return copy.deepcopy(plan)

    def _swap(plan):

        meet, team_rooms, equal_rows, startrole = cal_stats(plan)

        multimeet = {}

        for id1, team1 in enumerate(meet):
            for id2, team2 in enumerate(team1):
                if len(team2) > 1:
                    if id1 + 1 in multimeet:
                        multimeet[id1 + 1] += team2
                    else:
                        multimeet[id1 + 1] = copy.copy(team2)
        # print(multimeet)

        ro = random.randrange(1, len(plan))
        f1i = random.randrange(0, len(plan[ro]))
        t1p = random.randrange(0, len(plan[ro][f1i]))

        if len(multimeet) > 0:

            t1 = random.choice(list(multimeet.keys()))
            f1 = random.choice(multimeet[t1])
            f1s = f1.split(" - ")
            ro = int(f1s[0]) - 1

            while ro == 0:
                t1 = random.choice(list(multimeet.keys()))
                f1 = random.choice(multimeet[t1])
                f1s = f1.split(" - ")
                ro = int(f1s[0]) - 1

            f1i = ord(f1s[1]) - ord("A")

            # print("round %d fi: %d"%(ro, f1i))

            t1p = plan[ro][f1i].index(t1)

        else:
            teamnr = len(meet)
            optimal4fights = ((teamnr % 3) * 4 / teamnr) * len(plan)

            for team in range(teamnr):
                rooms = [tr[team] for tr in team_rooms]

                room4 = sum(map(bool, rooms))
                if room4 < math.floor(optimal4fights) or room4 > math.ceil(
                    optimal4fights
                ):
                    actrooms = list(
                        filter(lambda x: x != None and not x.startswith("1 "), rooms)
                    )
                    if len(actrooms) > 0:
                        # print("move 4")
                        f1 = random.choice(actrooms)
                        f1s = f1.split(" - ")
                        ro = int(f1s[0]) - 1
                        f1i = ord(f1s[1]) - ord("A")

                        t1p = plan[ro][f1i].index(team + 1)

        fi2 = random.randrange(0, len(plan[ro]))

        t2 = random.randrange(0, len(plan[ro][fi2]))

        tmp = plan[ro][f1i][t1p]
        plan[ro][f1i][t1p] = plan[ro][fi2][t2]
        plan[ro][fi2][t2] = tmp

        return plan

    def _initial(teams, rounds):
        plan = []
        rooms = teams // 3
        room4 = teams % 3

        for round in range(rounds):
            r = []
            tnr = list(range(1, teams + 1))
            if round > 0:
                random.shuffle(tnr)
            for r4 in range(room4):
                roomteams = tnr[:4]
                tnr = tnr[4:]
                r.append(roomteams)
            for r3 in range(rooms - room4):
                roomteams = tnr[:3]
                tnr = tnr[3:]
                r.append(roomteams)
            plan.append(r)

        return plan

    plan = _initial(teams, rounds)

    # calculate costs of plan
    cost = _cost(plan)
    best_plan = _copy(plan)
    best_cost = cost

    total_rounds = simulation_rounds
    cooling_base = 0.99

    cost_graph = []
    best_cost_graph = []
    for i in range(total_rounds):
        new_plan = _swap(plan)
        new_cost = _cost(new_plan)

        if i % 10000 == 0:
            print("r %d -> %s, best: %s" % (i, new_cost, best_cost))

        cost_graph.append(new_cost)
        best_cost_graph.append(best_cost)

        if new_cost["total"] < cost["total"] or random.random() < (cooling_base**i):
            cost = new_cost
            plan = new_plan

        if new_cost["total"] < best_cost["total"]:
            best_cost = new_cost
            best_plan = _copy(new_plan)

    return best_plan


def cal_startrole(plan):
    teams = sum(map(len, plan[0]))
    startrole = [[0, 0, 0, 0] for i in range(teams)]

    for ridx, round in enumerate(plan):
        for fidx, fight in enumerate(round):
            for rlidx, team1 in enumerate(fight):
                startrole[team1 - 1][rlidx] += 1

    return startrole


def fix_roles(plan):
    startroles = cal_startrole(plan)

    # print("before")
    # print(startroles)

    violations = len(list(filter(lambda x: x > 2, [x for y in startroles for x in y])))

    for i in range(10000):

        startroles = cal_startrole(plan)
        violations = len(
            list(filter(lambda x: x > 2, [x for y in startroles for x in y]))
        )
        # print(violations)
        if violations == 0:
            break

        found = False
        for tidx, team in enumerate(startroles):
            if random.random() > 2 / len(startroles):
                continue

            minrole = min(team)
            maxrole = max(team)

            if maxrole > 2 or random.random() < 0.99**i:
                for round in plan:
                    for fight in round:
                        if tidx + 1 in fight:
                            if fight.index(tidx + 1) == team.index(maxrole):

                                found = True
                                # print("fight before")
                                # print(fight)
                                hasidx = fight.index(tidx + 1)
                                try:
                                    changeteam = fight[team.index(minrole)]
                                except:
                                    changeteam = random.choice(
                                        list(filter(lambda x: x != tidx + 1, fight))
                                    )

                                chidx = fight.index(changeteam)
                                fight[chidx] = tidx + 1
                                fight[hasidx] = changeteam

                                # print("fight after")
                                # print(fight)
                                break
                        if found:
                            break
                    if found:
                        break
            if found:
                break

    startroles = cal_startrole(plan)
    # print("after")
    # print(startroles)
    return plan


def cal_stats(plan):

    teams = sum(map(len, plan[0]))

    meet = [[[] for i in range(teams)] for j in range(teams)]

    startrole = [[0, 0, 0, 0] for i in range(teams)]

    max_cap = 0

    for room in plan[0]:
        if len(room) > max_cap:
            max_cap = len(room)

    maxr_teams = [[] for i in range(teams)]
    max_cap_max = 0

    for ridx, round in enumerate(plan):
        for fidx, fight in enumerate(round):
            # teams = list(map(lambda x:x[0], fight.templateattendance_set.all().values_list("team")))
            short_fightstr = "%d - %s" % (ridx + 1, chr(ord("A") + fidx))
            for rlidx, team1 in enumerate(fight):
                if len(fight) == 4:
                    maxr_teams[team1 - 1].append(short_fightstr)
                    if len(maxr_teams[team1 - 1]) > max_cap_max:
                        max_cap_max = len(maxr_teams[team1 - 1])
                startrole[team1 - 1][rlidx] += 1
                for team2 in fight:
                    if team1 != team2:
                        meet[team1 - 1][team2 - 1].append(short_fightstr)

    team_rooms = [[None for i in range(teams)] for j in range(max_cap_max)]

    for idx, maxr_team in enumerate(maxr_teams):
        for ydx, room in enumerate(maxr_team):
            team_rooms[ydx][idx] = room

    equal_rows = 0
    for row in team_rooms:
        if all(map(bool, row)):
            equal_rows += 1

    return (meet, team_rooms, equal_rows, startrole)


def plan_yaml_dump(teams, plan, roomnames, meta=None):
    import yaml

    if meta == None:
        meta = {}

    meta_data = {
        **meta,
        "name": "your_name",
        "teams": teams,
        "rooms": roomnames[: (teams // 3)],
    }

    root = {"meta": meta_data, "rounds": []}

    # print(plan)

    for round in plan:
        ro = []
        for fix, fight in enumerate(round):
            fi = {}
            fi["name"] = roomnames[fix]
            fi["rep"] = fight[0]
            fi["opp"] = fight[1]
            fi["rev"] = fight[2]
            if len(fight) > 3:
                fi["obs"] = fight[3]
            ro.append(fi)
        root["rounds"].append(ro)
    return yaml.dump(root)
