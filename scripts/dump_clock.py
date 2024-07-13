import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc.settings")

print(os.path.abspath(__file__ + "/../../"))

sys.path.append(os.path.abspath(__file__ + "/../../"))

import django
django.setup()

from apps.fight.models import ClockState

from apps.tournament.models import Tournament

import json

trn = Tournament.objects.get(slug=sys.argv[1])

print(trn)

states = ClockState.objects.filter(stage__fight__round__tournament=trn)

data = []

for s in states:
    data.append({"round":s.stage.fight.round.order,"room":s.stage.fight.room.name,"stage":s.stage.order,
                 "phase":s.phase.id, "elapsed":s.elapsed,"time":str(s.server_time)})

with open(sys.argv[2],"w") as out:
    json.dump(data,out)

