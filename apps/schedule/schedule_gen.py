import sys
from multiprocessing import Pool

from generator import _cost, cal_stats, fix_roles, generate_plan, plan_yaml_dump

teams = int(sys.argv[1])
rounds = int(sys.argv[2])
simulation = int(sys.argv[3])

runs = 10
if len(sys.argv) > 4:
    runs = int(sys.argv[4])

threads = 4
if len(sys.argv) > 5:
    treads = int(sys.argv[5])

direc = "."
if len(sys.argv) > 6:
    direc = sys.argv[6]


def work(file):

    plan = generate_plan(teams, rounds, simulation)

    plan = fix_roles(plan)

    meet, team_rooms, equal_rows, startrole = cal_stats(plan)

    roomnames = [chr(i) for i in range(ord("A"), ord("Z"))]

    m = {}

    doublemeets = 0
    for round in meet:
        for fight in round:
            if len(fight) > 1:
                doublemeets += 1
    m["n_meet_multiple"] = doublemeets
    m["d_4fight"] = len(team_rooms) - equal_rows
    m["max_4fight"] = len(team_rooms)
    m["cost"] = _cost(plan)
    m["role_violations"] = len(
        list(filter(lambda x: x > 2, [x for y in startrole for x in y]))
    )
    m["simulation_rounds"] = simulation

    yamlstr = plan_yaml_dump(teams, plan, roomnames, meta=m)

    with open(file, "w") as f:
        f.write(yamlstr)


files = ["%s/result-%04d.yml" % (direc, d) for d in range(runs)]


with Pool(processes=treads) as pool:
    res = pool.map(work, files)
