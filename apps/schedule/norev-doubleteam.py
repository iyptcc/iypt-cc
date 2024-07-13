import random
import sys

nteams = 17

team_conflict = {1: 0, 0: 1, 2: 3, 3: 2}  # , 4: 5, 5: 4}

plan = []


def initplan():
    global plan
    if nteams % 2 == 0:
        tworooms = nteams // 2
        threerooms = 0
    else:
        tworooms = nteams // 2 - 1
        threerooms = 1
    plan = [
        [[None, None] for _ in range(tworooms)]
        + [[None, None, None] for _ in range(threerooms)]
        for _ in range(5)
    ]
    assigned = []
    missing = list(range(nteams))
    for fi, f in enumerate(plan[0]):
        for ti, _ in enumerate(f):
            assign = None
            for m in missing:
                if m in assigned or (
                    m in team_conflict and team_conflict[m] in plan[0][fi]
                ):
                    continue
                assign = m
                break
            missing.remove(assign)
            plan[0][fi][ti] = assign
            assigned.append(assign)


def previnround(ro, team):
    return team in [r for x in plan[ro] for r in x]


def oftenrole(ro, team, pos):
    role = 0
    for rou in plan[:ro]:
        for fi in rou:
            if pos == 0:
                if team == fi[0]:
                    role += 1
            else:
                if team in fi[1:]:
                    role += 1
    if role > 2:
        return True
    return False


def prevmeet(ro, team, meetnow):
    # print("premeet", ro, team, meetnow)
    prevmeet = False
    for rou in plan[:ro]:
        for fi in rou:
            if team in fi:
                for opp in meetnow:
                    if opp in fi:
                        return True
    return False


def alreadytwice3(ro, team):
    # print("premeet", ro, team, meetnow)
    prevthree = 0
    for rou in plan[:ro]:
        if team in rou[-1]:
            prevthree += 1

    if prevthree > 1:
        return True
    return False


def alreadyonce3(ro, team):
    # print("premeet", ro, team, meetnow)
    prevthree = 0
    for rou in plan[:ro]:
        if team in rou[-1]:
            prevthree += 1

    if prevthree > 0:
        return True
    return False


def conflict_in_fight(team, meetnow):
    for m in meetnow:
        if m in team_conflict and team_conflict[m] == team:
            return True
    return False


tries = 0


def findnext(ro, fight, pos):
    global tries

    if tries > 2000:
        print("timeout")
        return 1

    if ro == 5:
        print("hooray")
        # show()
        return 1
        # sys.exit(0)

    # show()
    # progress()

    impossible = set()  # list(range(nteams)))

    # if plan[ro][fight][pos] is None:
    #    nxt = 0
    # else:
    #    nxt = plan[ro][fight][pos] + 1

    for t in range(nteams):
        if previnround(ro, t):
            impossible.add(t)

    for t in range(nteams):
        if prevmeet(ro, t, plan[ro][fight][:pos]):
            # pass
            impossible.add(t)

    for t in range(nteams):
        if oftenrole(ro, t, pos):
            impossible.add(t)
            # pass

    for t in range(nteams):
        if conflict_in_fight(t, plan[ro][fight][:pos]):
            impossible.add(t)

    for t in range(nteams):
        # if len(plan[ro][fight]) == 3 and alreadytwice3(ro, t):
        if len(plan[ro][fight]) == 3 and alreadyonce3(ro, t):
            impossible.add(t)

    possible = list(set(list(range(nteams))) - impossible)
    # print("possible:",possible)
    random.shuffle(possible)
    for t in possible:
        plan[ro][fight][pos] = t

        npos = pos + 1
        nfight = fight
        nro = ro
        if npos == len(plan[ro][fight]):
            npos = 0
            nfight = fight + 1
        if nfight == len(plan[ro]):
            nro = ro + 1
            nfight = 0

        tries += 1

        if findnext(nro, nfight, npos) == 1:
            return 1

    plan[ro][fight][pos] = None

    # if nxt == nteams:
    #    print("no valid found")
    #    plan[ro][fight][pos] = None
    #    npos = pos - 1
    #    nfight = fight
    #    nro = ro
    #    if npos < 0 and fight == 0:
    #        nro = ro - 1
    #        nfight = len(plan[0])-1
    #        npos = len(plan[0][-1])-1
    #    elif npos < 0:
    #        nfight = fight - 1
    #        npos = len(plan[0][nfight])-1
    #
    #    return findnext(nro,nfight,npos)


def valid():
    pass


def show():
    for ri, _ in enumerate(plan):
        for fi, _ in enumerate(plan[0]):
            print(f"f {fi} r {ri}: {plan[ri][fi]}", end=" | ")
        print("")


def progress():
    count = 0
    for ri, _ in enumerate(plan):
        for fi, _ in enumerate(plan[0]):
            for team in plan[ri][fi]:
                if team is not None:
                    count += 1
    print(len(plan) * nteams, count, tries)
    return count == len(plan) * nteams


def oddroundcost():
    if nteams % 2 == 0:
        return True
    long = {t: 0 for t in range(nteams)}
    # print("long", long)
    for rol in plan:
        # print("rol", rol)
        for team in rol[-1]:
            # print("increment", team)
            long[team] += 1
    print(long.values())
    if min(*long.values()) < 1 or max(*long.values()) > 2:
        return False
    return True


def fixstartrole():
    pres = {}
    for rol in plan:
        for fi in rol:
            if fi[0] not in pres:
                pres[fi[0]] = 0
            pres[fi[0]] += 1
    print(pres.values())


initplan()
show()
findnext(1, 0, 0)
print("found next")
print(progress())
while not progress():
    tries = 0
    initplan()
    findnext(1, 0, 0)

show()
print("found")
print("oddround", oddroundcost())
# sys.exit(0)
while False:
    # while not oddroundcost():
    initplan()
    while not progress():
        tries = 0
        initplan()
        # print("inited plan", plan)
        findnext(1, 0, 0)
    print("found plan, check for oddroundcost")
    # initplan()
    # findnext(1, 0, 0)

show()
fixstartrole()

show()

# sys.exit(0)
import yaml


def generate_yaml():

    roomnames = [chr(i) for i in range(ord("A"), ord("Z"))]

    meta_data = {
        "name": "your_name_norev",
        "teams": nteams,
        "rooms": roomnames[: (nteams // 2)],
    }

    root = {"meta": meta_data, "rounds": []}

    # print(plan)

    for round in plan:
        ro = []
        for fix, fight in enumerate(round):
            fi = {}
            fi["name"] = roomnames[fix]
            fi["rep"] = fight[0] + 1
            fi["opp"] = fight[1] + 1
            if len(fight) > 2:
                fi["obs"] = fight[2] + 1
            ro.append(fi)
        root["rounds"].append(ro)
    return yaml.dump(root)


yamlstr = generate_yaml()

with open(sys.argv[1], "w") as f:
    f.write(yamlstr)
