from __future__ import absolute_import, unicode_literals

from datetime import datetime

from celery import current_task, shared_task

from apps.jury.models import AssignResult
from apps.plan.models import Round
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname

from .anealing import assignAneal
from .utils import create_fight_gradingsheets


@shared_task
def assignJob(
    tournament_id, total_rounds=1000, room_jurors=5, cooling_base=0.99, fix_rounds=0
):

    # prepare return object from best_plan

    best_plan, best_cost = assignAneal(
        tournament_id, total_rounds, room_jurors, cooling_base, fix_rounds, current_task
    )

    if len(best_plan) == 0:
        return ([], best_cost)

    plan = []

    for round in best_plan:

        round_fights = []

        for fight in round["fights"]:

            fight_data = {
                "pk": fight["fight"].pk,
                "room": fight["fight"].room.name,
                "jurors": [],
                "nonvoting": [],
            }

            chair = fight["jurors"][0]
            poss_chairs = list(filter(lambda j: j.possible_chair, fight["jurors"]))
            if len(poss_chairs) > 0:
                chair = poss_chairs[0]

            fight_data["chair"] = {"id": chair.pk, "name": chair.attendee.full_name}

            for juror in fight["jurors"]:
                if juror != chair:
                    fight_data["jurors"].append(
                        {"id": juror.pk, "name": juror.attendee.full_name}
                    )

            for juror in fight["nonvoting"]:
                fight_data["nonvoting"].append(
                    {"id": juror.pk, "name": juror.attendee.full_name}
                )

            round_fights.append(fight_data)

        plan.append(round_fights)

    ar = AssignResult.objects.get(task_id=current_task.request.id)
    ar.finished = datetime.now()
    ar.save()

    return (plan, best_cost)


@shared_task
def renderFeedback(baseurl, round_id):

    round = Round.objects.get(pk=round_id)
    trn = round.tournament

    for fight in round.fight_set.all():

        context = context_generator.juryfeedback(baseurl, fight)

        fileprefix = "jury-feedback-round-%d-room-%s-v" % (round.order, fight.room.name)

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.JURYFEEDBACK).id,
            pdf.id,
            context=context,
        )

        pdf.task_id = res.id
        pdf.save()

        try:
            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.JURYFEEDBACK))
        except:
            pass

        fight.pdf_jury_feedback = pdf
        fight.save()

    return None


@shared_task
def renderSheets(round_id):

    round = Round.objects.get(pk=round_id)

    for fight in round.fight_set.all():
        create_fight_gradingsheets(fight)

    return None
