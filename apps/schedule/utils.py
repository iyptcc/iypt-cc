import yaml

from apps.tournament.models import (
    ScheduleTemplate,
    TemplateAttendance,
    TemplateFight,
    TemplateRoom,
    TemplateRound,
)


def import_template(file):
    with open(file) as f:
        sched = yaml.load(f, Loader=yaml.SafeLoader)
        print(sched)

        st = ScheduleTemplate.objects.get_or_create(
            name=sched["meta"]["name"], teams=int(sched["meta"]["teams"])
        )[0]

        for room in sched["meta"]["rooms"]:
            TemplateRoom.objects.get_or_create(template=st, name=room)

        for rnr, round in enumerate(sched["rounds"]):
            tr = TemplateRound.objects.get_or_create(order=(rnr + 1), template=st)[0]
            for fight in round:
                tf = TemplateFight.objects.get_or_create(
                    room=TemplateRoom.objects.get(template=st, name=fight["name"]),
                    round=tr,
                )[0]
                for type, n in TemplateAttendance.ROLE_TYPE:
                    if type in fight:
                        TemplateAttendance.objects.get_or_create(
                            type=type, team=fight[type], fight=tf
                        )
