
from apps.registration.models import AttendeePropertyValue
from apps.team.models import TeamRole

from .models import Payment, PropertyFee


def get_subpayments(payments):
    inp = []
    pend = 0
    amt = 0
    for p in payments:
        amt += p.amount
        if not p.cleared_at and not p.aborted_at:
            pend+= p.amount
        subpayments = []
        sp = p
        print(p.payment_set.all())
        while sp.payment_set.exists():
            sp = sp.payment_set.first()
            subpayments.append(sp)
            if sp.aborted_at:
                amt -= sp.amount
            if not sp.cleared_at and not sp.aborted_at:
                pend += sp.amount

        inp.append({"payment":p,"subpayments":subpayments})

    return inp, amt, pend

def expected_fees(team):
    fees = []
    # team fee
    if team.tournament.fee_team:
        fees.append({"name":"Team fee for %s"%team.origin.name, "amount":team.tournament.fee_team, 'type':Payment.TEAM})
    # role fee
    for ass in team.teammember_set.filter(role__type=TeamRole.ASSOCIATED):
        for pr in ass.attendee.roles.all():
            if pr.fee:
                fees.append({"name":"%s fee for %s"%(pr.get_type_display(), ass.attendee.full_name), "amount":pr.fee, 'type':Payment.ROLE, 'role':pr, 'attendee':ass.attendee})
    # property fee
    for att in team.members.all():
        for pf in PropertyFee.objects.filter(tournament=team.tournament):
            alltrue = True
            for trues in pf.if_true.all():
                try:
                    apv = AttendeePropertyValue.objects.filter(property=trues, attendee=att).last()
                    value = getattr(apv, apv.field_name[trues.type])
                    if value != True:
                        alltrue = False
                except:
                    alltrue = False
            allfalse = True
            for falses in pf.if_not_true.all():
                try:
                    apv = AttendeePropertyValue.objects.filter(property=falses, attendee=att).last()
                    value = getattr(apv, apv.field_name[falses.type])
                    if value != False:
                        allfalse = False
                except:
                    pass
            if alltrue and allfalse:
                fees.append({"name":"%s fee for %s"%(pf.name, att.full_name), "amount":pf.fee, 'type':Payment.PROPERTY, 'attendee':att, 'property':pf})

    return fees


def expected_person_fees(attendee):
    fees = []

    # role fee
    for pr in attendee.roles.all():
        if pr.fee:
            fees.append(
                {"name": "%s fee for %s" % (pr.get_type_display(), attendee.full_name), "amount": pr.fee})
    # property fee
    for pf in PropertyFee.objects.filter(tournament=attendee.tournament):
        alltrue = True
        for trues in pf.if_true.all():
            try:
                apv = AttendeePropertyValue.objects.filter(property=trues, attendee=attendee).last()
                value = getattr(apv, apv.field_name[trues.type])
                if value != True:
                    alltrue = False
            except:
                alltrue = False
        allfalse = True
        for falses in pf.if_not_true.all():
            try:
                apv = AttendeePropertyValue.objects.filter(property=falses, attendee=attendee).last()
                value = getattr(apv, apv.field_name[falses.type])
                if value != False:
                    allfalse = False
            except:
                pass
        if alltrue and allfalse:
            fees.append({"name": "%s fee for %s" % (pf.name, attendee.full_name), "amount": pf.fee})

    return fees
