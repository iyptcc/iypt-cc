import copy
import math
import random

g_rounds = 0
g_teams = 0
g_rooms = 0
g_rooms4 = 0
g_iters = 0

g_found = False


def _check_valid(plan):
    meet = [[[] for i in range(g_teams)] for j in range(g_teams)]

    optimal4fights = ((g_teams % 3) * 4 / g_teams) * g_rounds

    in4fi = [0 for i in range(g_teams)]

    for ridx, round in enumerate(plan):
        for fidx, fight in enumerate(round):
            # teams = list(map(lambda x:x[0], fight.templateattendance_set.all().values_list("team")))
            short_fightstr = "%d - %s" % (ridx + 1, chr(ord("A") + fidx))
            for rlidx, team1 in enumerate(fight):
                if len(fight) == 4:
                    in4fi[team1 - 1] += 1
                for team2 in fight:
                    if team1 != team2:
                        meet[team1 - 1][team2 - 1].append(short_fightstr)

    costmeet = 0
    for team1 in meet:
        for team2 in team1:
            if len(team2) > 1:
                costmeet += 1
    if len(plan) == g_rounds:
        cost4 = list(
            filter(
                lambda x: x < math.floor(optimal4fights)
                or x > math.ceil(optimal4fights),
                in4fi,
            )
        )
    else:
        cost4 = list(filter(lambda x: x > math.ceil(optimal4fights), in4fi))
    # print(cost4)
    return costmeet + len(cost4) == 0


def find_next(partial_plan):

    global g_found, g_iters

    g_iters += 1

    if g_iters % 1000 == 0:
        print("%d", g_iters)
        print(partial_plan)

    if g_found:
        return

    plan = copy.deepcopy(partial_plan)

    # print("called with")
    # print(plan)

    # finish
    if len(plan) == g_rounds and len(plan[-1]) == g_rooms and len(plan[-1][-1]) == 3:
        print("finished")
        print(plan)
        g_found = True
        return

    # start new round
    # print("in find_next with")
    # print(partial_plan)
    # print("len %d len fight %d"%(len(partial_plan[-1]),len(partial_plan[-1][-1])))
    # print("rooms %d"%g_rooms)
    if len(plan[-1]) == g_rooms and len(plan[-1][-1]) == 3:
        plan.append([[]])
        find_next(plan)

    # handle 4 fight
    elif len(plan[-1]) <= g_rooms:
        fullfight = 3
        if len(plan[-1]) <= g_rooms4:
            fullfight = 4
        # print("fullfight")
        # print(fullfight)
        if len(plan[-1][-1]) < fullfight:
            # in 4 fight
            # teams already in round

            # print("add team to fight")
            tir = list(
                set(range(1, g_teams + 1))
                - set([item for sublist in plan[-1] for item in sublist])
            )
            # print("can add")
            # print(tir)
            random.shuffle(tir)
            for team in tir:
                new_plan = copy.deepcopy(plan)
                new_plan[-1][-1].append(team)
                # check for validity
                if _check_valid(plan):
                    find_next(new_plan)
        else:
            # start new 4 fight
            # print("start new fight")
            plan[-1].append([])
            find_next(plan)


def generate_plan(teams, rounds):

    global g_rooms, g_teams, g_rounds, g_rooms4
    g_rounds = rounds
    g_teams = teams
    rooms = teams // 3
    room4 = teams % 3
    g_rooms = rooms
    g_rooms4 = room4

    plan = []

    r = []
    tnr = list(range(1, teams + 1))
    for r4 in range(room4):
        roomteams = tnr[:4]
        tnr = tnr[4:]
        r.append(roomteams)
    for r3 in range(rooms - room4):
        roomteams = tnr[:3]
        tnr = tnr[3:]
        r.append(roomteams)
    plan.append(r)

    print(plan)

    find_next(plan)


if __name__ == "__main__":
    generate_plan(14, 3)
