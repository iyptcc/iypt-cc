from __future__ import absolute_import, unicode_literals

from datetime import datetime

from celery import current_task, shared_task

from apps.jury.models import AssignResult

from .anealing import assignAneal


@shared_task
def assignJob(tournament_id, total_rounds=1000, room_jurors=5, cooling_base=0.99, fix_rounds=0):

    # prepare return object from best_plan

    best_plan, best_cost = assignAneal(tournament_id, total_rounds, room_jurors, cooling_base, fix_rounds, current_task)

    if len(best_plan) == 0:
        return ([],best_cost)

    plan = []

    for round in best_plan:


        round_fights = []

        for fight in round["fights"]:

            fight_data = {"pk": fight["fight"].pk, 'room': fight["fight"].room.name, 'jurors': [], "nonvoting":[]}

            chair = list(filter(lambda j: j.possible_chair, fight['jurors']))[0]

            fight_data['chair'] = {'id': chair.pk, "name": chair.attendee.full_name}

            for juror in fight["jurors"]:
                if juror != chair:
                    fight_data['jurors'].append({'id': juror.pk, "name": juror.attendee.full_name})

            for juror in fight["nonvoting"]:
                fight_data['nonvoting'].append({'id': juror.pk, "name": juror.attendee.full_name})

            round_fights.append(fight_data)

        plan.append(round_fights)

    ar = AssignResult.objects.get(task_id=current_task.request.id)
    ar.finished = datetime.now()
    ar.save()

    return (plan, best_cost)
