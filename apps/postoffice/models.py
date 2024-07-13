from django.db import models
from django.db.models import Q

from apps.tournament.models import Tournament

# Create your models here.


class Template(models.Model):

    name = models.CharField(max_length=200)
    tournament = models.ForeignKey(
        Tournament, related_name="mailtemplates", on_delete=models.CASCADE
    )

    REGISTRATION = "registration"
    JURORFEEDBACK = "jurorfeedback"
    TYPE = (
        (REGISTRATION, "Registration"),
        (JURORFEEDBACK, "Juror Feedback"),
    )

    type = models.CharField(max_length=25, choices=TYPE, blank=True, null=True)

    def __str__(self):
        return "%s" % self.name

    class Meta:
        unique_together = ("name", "tournament")


class DefaultTemplate(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    tournament = models.ForeignKey(
        Tournament, related_name="default_mail_template", on_delete=models.CASCADE
    )

    type = models.CharField(max_length=25, choices=Template.TYPE)

    class Meta:
        unique_together = ("tournament", "type")


class TemplateVersion(models.Model):

    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    creation = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(
        "account.ActiveUser",
        related_name="mailtemplateversions",
        on_delete=models.CASCADE,
    )

    subject = models.CharField(max_length=1000, blank=True)

    src = models.TextField(blank=True)

    def __str__(self):
        return "%s @ %s" % (self.template.name, self.creation)
