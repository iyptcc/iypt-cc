from django.db import models
from django.utils.timezone import now

from apps.account.models import Attendee
from apps.plan.models import Stage
from apps.printer.models import Pdf
from apps.tournament.models import Phase, Tournament

# Create your models here.


class ClockState(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE)
    server_time = models.DateTimeField(default=now)

    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)
    elapsed = models.IntegerField()

    def __str__(self):
        return "%s in %s elapsed %d @ %s" % (
            self.stage,
            self.phase,
            self.elapsed,
            self.server_time,
        )

    class Meta:
        ordering = ("server_time",)


class ScanProcessing(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=255)
    pdf = models.ForeignKey(Pdf, on_delete=models.SET_NULL, null=True)

    author = models.ForeignKey(
        Attendee, blank=True, null=True, on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    finished = models.DateTimeField(null=True, blank=True)

    error_pages = models.IntegerField(blank=True, null=True)
