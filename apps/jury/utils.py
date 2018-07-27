from .models import Juror, JurorRole


def check_conflict_origin(fight, juror):
    participant_origins = set(
        fight.stage_set.get(order=1).attendees.all().values_list("origin_id", flat=True))
    conflicting = set(juror.conflicting.all().values_list("id", flat=True))

    if len(participant_origins & conflicting) != 0:
        return True

    return False

def plan_from_db(tournament):
    plan = []
    for round in tournament.round_set(manager='selectives').all():
        ro = []
        for fight in round.fight_set.all():
            fi = {'jurors':[]}
            for js in fight.jurorsession_set.filter(role__type__in=[JurorRole.JUROR, JurorRole.CHAIR]):
                fi['jurors'].append({'id': js.juror.pk, "name": js.juror.attendee.full_name})
            ro.append(fi)
        plan.append(ro)
    return plan

def async_plan_from_db(tournament):

    plan=[]
    for round in tournament.round_set(manager='selectives').all():
        round_fights = {"fights": []}

        for fight in round.fight_set.all():
            fight_data = {"fight": fight, 'jurors': [], "nonvoting": []}

            fight_data['jurors'] = [js.juror for js in list(fight.jurorsession_set(manager="voting").all())]

            round_fights["fights"].append(fight_data)
        plan.append(round_fights)

    return plan

def plan_cost(plan, jurors):
    """
    calculate the cost of a plan
    :param plan: the plan
    :param jurors: all jurors
    :return:
    """

    # collect assignments of jurors for the whole tournament
    assignments={}
    exp_assignments = {}
    empty = set(jurors)
    exp_jurors = [j for j in jurors if j.experience==Juror.EXPERIENCE_HIGH]
    exp_empty = set(exp_jurors)
    bias_total = 0
    for round in plan:
        for fight in round["fights"]:
            fi = fight
            js=fi["jurors"]
            empty -= set(js)
            bias_mean = 0
            for j in js:
                bias_mean += j.bias
                if j.pk in assignments:
                    assignments[j.pk] += 1
                else:
                    assignments[j.pk] = 1
                if j.experience == Juror.EXPERIENCE_HIGH:
                    exp_empty -= set(js)
                    if j.pk in exp_assignments:
                        exp_assignments[j.pk] += 1
                    else:
                        exp_assignments[j.pk] = 1

            bias_total += (bias_mean**2)

    # every juror with more or less assignments as average costs quadratic
    avg_assign = sum(assignments.values())/len(jurors)
    assign_cost = 0
    for a in assignments.values():
        assign_cost += abs(avg_assign-a)**2
    assign_cost+=len(empty)*(avg_assign**2)

    exp_assign_cost = 0
    if len(exp_jurors) > 0:
        exp_avg_assign = sum(exp_assignments.values())/len(exp_jurors)
        for a in exp_assignments.values():
            exp_assign_cost += abs(exp_avg_assign - a) ** 2
        exp_assign_cost += len(exp_empty) * (exp_avg_assign ** 2)

    # chair meets team twice cost
    chairmeets = {}

    for round in plan:
        for f in round['fights']:
            chairs = list(filter(lambda j: j.possible_chair, f['jurors']))
            if len(chairs) == 0:
                continue
            chair = chairs[0]
            fight_origins = list(f["fight"].stage_set.get(order=1).attendees.all().values_list("origin_id", flat=True))
            if chair.pk not in chairmeets:
                chairmeets[chair.pk]=fight_origins
            else:
                chairmeets[chair.pk]+=fight_origins

    chairMeetTwice = 0
    for chair,sees in chairmeets.items():
        chairMeetTwice += len(sees) - len(set(sees))

    #juror meets team often

    jurormeets = {}

    for round in plan:
        for f in round['fights']:
            for j in f['jurors']:
                fight_origins = list(f["fight"].stage_set.get(order=1).attendees.all().values_list("origin_id", flat=True))
                if j.pk not in jurormeets:
                    jurormeets[j.pk] = fight_origins
                else:
                    jurormeets[j.pk] += fight_origins

    jurorMeetOften = 0
    for juror, sees in jurormeets.items():
        jurorMeetOften += len(sees) - len(set(sees))

    #jurors from same country

    same_country = 0

    for round in plan:
        for f in round['fights']:
            juror_conflicts = []
            for j in f["jurors"]:
                juror_conflicts+=list(j.conflicting.all().values_list("id", flat=True))
            same_country += len(juror_conflicts) - len(set(juror_conflicts))


    trn = jurors[0].attendee.tournament

    cost_obj = {}
    cost_obj['total'] = trn.jury_opt_weight_assignmentbalance * assign_cost \
                        + trn.jury_opt_weight_expassignmentbalance * exp_assign_cost \
                        + trn.jury_opt_weight_teamandchairmeettwice * chairMeetTwice \
                        + trn.jury_opt_weight_teamandjurormeetmultiple * jurorMeetOften \
                        + trn.jury_opt_weight_jurysamecountry * same_country \
                        + trn.jury_opt_weight_bias * bias_total
    cost_obj['assignmentBalance'] = assign_cost
    cost_obj['ExpAssignmentBalance'] = exp_assign_cost
    cost_obj['teamAndChairMeetTwice'] = chairMeetTwice
    cost_obj['teamAndJurorMeetMultiple'] = jurorMeetOften
    cost_obj['jurySameCountry'] = same_country
    cost_obj['bias'] = bias_total


    return cost_obj

def assignments_light(plan, jurors):
    # collect assignments of jurors for the whole tournament
    assignments = {}
    empty = set(jurors.values_list('id',flat=True))
    for round in plan:
        for fight in round:
            fi = fight
            js = fi["jurors"]
            if 'chair' in fi:
                js.append(fi["chair"])
            empty -= set([j['id'] for j in js])
            for j in js:
                if j['id'] in assignments:
                    assignments[j['id']] += 1
                else:
                    assignments[j['id']] = 1
    
    batches = {}

    for k,v in assignments.items():
        if v not in batches:
            batches[v]=[jurors.get(pk=k)]
        else:
            batches[v].append(jurors.get(pk=k))

    bli = []
    for i in range(len(plan)+1):
        if i in batches:
            bli.append(batches[i])
        else:
            bli.append([])
    return bli
