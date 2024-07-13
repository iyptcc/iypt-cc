from datetime import date

from celery import shared_task

from apps.tournament.models import Tournament

from .bbb import get_attendees, get_hall_attendees


@shared_task
def syncbbb():
    for trn in Tournament.objects.filter(
        date_start__lte=date.today(), date_end__gte=date.today()
    ):
        for ro in trn.round_set.all():
            for fi in ro.fight_set.all():
                get_attendees(fi)
        for hall in trn.hall_set.all():
            get_hall_attendees(hall)
