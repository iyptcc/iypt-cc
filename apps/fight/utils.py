from apps.jury.models import JurorGrade


def fight_grades_valid(fight):
    vl = list(JurorGrade.objects.filter(stage_attendee__stage__fight=fight).values_list("valid", flat=True))
    return ( len(vl) > 0 and all(vl) )
