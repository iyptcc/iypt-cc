from django.db import models
from django.db.models import Q

from apps.account.models import Attendee, ParticipationRole
from apps.registration.models import AttendeeProperty
from apps.team.models import Team
from apps.tournament.models import Tournament

# Create your models here.

class Account(models.Model):
    owners = models.ManyToManyField(Attendee)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=True, blank=True)

    address = models.TextField(null=True, blank=True)

    def __str__(self):
        names = []
        if self.team:
            names.append("%s"%self.team)
        if self.name:
            names.append("%s"%self.name)
        return "%s: %s"%(", ".join(map(str,self.owners.all())),", ".join(names))


class PropertyFee(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    fee = models.DecimalField(max_digits=10, decimal_places=2)

    if_true = models.ManyToManyField(AttendeeProperty, related_name="true_propertyfee", blank=True)
    if_not_true = models.ManyToManyField(AttendeeProperty, related_name="not_true_propertyfee", blank=True)


class Payment(models.Model):

    TEAM = 'team'
    ROLE = 'role'
    PROPERTY = 'property'
    PAYMENT_TYPE = (
        (TEAM, 'Team'),
        (ROLE, 'Role'),
        (PROPERTY, 'Property'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Attendee, on_delete=models.CASCADE)

    sender = models.ForeignKey(Account, related_name="outgoing_payments", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    reference = models.TextField()

    ref_type = models.CharField(max_length=30, choices=PAYMENT_TYPE, null=True, blank=True)
    ref_team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.CASCADE)
    ref_role = models.ForeignKey(ParticipationRole, null=True, blank=True, on_delete=models.CASCADE)
    ref_property = models.ForeignKey(PropertyFee, null=True, blank=True, on_delete=models.CASCADE)
    ref_attendee = models.ForeignKey(Attendee, null=True, blank=True, related_name="reference_attendee", on_delete=models.CASCADE)

    receiver = models.ForeignKey(Account, related_name="incoming_payments", on_delete=models.CASCADE)

    due_at = models.DateTimeField(blank=True, null=True)

    aborted_at = models.DateTimeField(blank=True, null=True)
    aborted_by = models.ForeignKey(Attendee, blank=True, null=True, related_name="aboarted_payments", on_delete=models.CASCADE)
    abort_reason = models.CharField(max_length=300, null=True, blank=True)

    cleared_at = models.DateTimeField(blank=True, null=True)
    cleared_by = models.ForeignKey(Attendee, blank=True, null=True, related_name="cleared_payments", on_delete=models.CASCADE)

    residual_of = models.ForeignKey("bank.Payment", blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return "%s -> %s: %s , %s"%(self.sender_id, self.receiver_id, self.amount, self.reference)
