from __future__ import absolute_import, unicode_literals

import json

from celery import current_task, shared_task
from django.contrib.admin.utils import NestedObjects
from django.utils.text import capfirst

from apps.tournament.models import Tournament


@shared_task
def scrubpreparePII(tournament_id, attendeeproperty, applicationquestion):
    trn = Tournament.objects.get(id=tournament_id)
    collector = NestedObjects(using="default")  # or specific database
    trn.scrub_attendee_property.clear()
    trn.scrub_application_question.clear()
    for att in trn.attendee_set.all():
        apvs = att.attendeepropertyvalue_set.exclude(property_id__in=attendeeproperty)
        collector.collect(apvs)
        trn.scrub_attendee_property.add(*apvs)

    for app in trn.application_set.all():
        aqvs = app.applicationquestionvalue_set.exclude(
            question_id__in=applicationquestion
        )
        collector.collect(aqvs)
        trn.scrub_application_question.add(*aqvs)

    def format_callback(obj):
        return "%s: %s" % (capfirst(obj._meta.verbose_name), obj)

    to_delete = collector.nested(format_callback)

    return to_delete


@shared_task
def scrubPII(tournament_id):
    trn = Tournament.objects.get(id=tournament_id)
    for apv in trn.scrub_attendee_property.all():
        apv.delete()
    for aqv in trn.scrub_application_question.all():
        aqv.delete()
    trn.scrub_task_id = None
    trn.save()
