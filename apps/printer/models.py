import datetime

from django.db import models
from django.db.models import Q

from apps.bank.models import Account
from apps.tournament.models import Tournament

# Create your models here.


class Template(models.Model):
    name = models.CharField(max_length=200)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self", null=True, blank=True, default=None, on_delete=models.CASCADE
    )

    PREVIEW = "preview"
    RANKING = "ranking"
    RESULTS = "results"
    JURYROUND = "jury_round"
    GRADING = "grading"
    GRADEOVERVIEW = "gradeoverview"
    TEAMROUND = "team_round"
    JURYFEEDBACK = "jury_feedback"
    PROBLEMSELECT = "problem_select"
    PERSONS = "persons"
    REGISTRATION = "registration"
    INVOICE = "invoice"
    TEAM = "team"
    TYPE = (
        (PREVIEW, "Preview"),
        (RANKING, "Ranking"),
        (RESULTS, "Results"),
        (JURYROUND, "Jury Round Plan"),
        (GRADING, "Grading Sheet"),
        (GRADEOVERVIEW, "Overview Grading Sheet"),
        (TEAMROUND, "Team Round Plan"),
        (JURYFEEDBACK, "Jury Fight Feedback"),
        (PROBLEMSELECT, "Problem Selection for last PF"),
        (PERSONS, "Persons"),
        (REGISTRATION, "Registration"),
        (INVOICE, "Invoice"),
        (TEAM, "Team"),
    )

    type = models.CharField(max_length=25, choices=TYPE, blank=True, null=True)

    files = models.ManyToManyField("printer.Pdf", blank=True)

    def all_files(self):
        f = self.files.all()
        if self.parent:
            f |= self.parent.all_files()
        return f

    def __str__(self):
        return "%s" % self.name


class DefaultTemplate(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    tournament = models.ForeignKey(
        Tournament, related_name="default_template", on_delete=models.CASCADE
    )

    type = models.CharField(max_length=25, choices=Template.TYPE)

    class Meta:
        unique_together = ("tournament", "type")


class TemplateVersion(models.Model):

    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    creation = models.DateTimeField(auto_now=True)
    author = models.ForeignKey("account.ActiveUser", on_delete=models.CASCADE)

    src = models.TextField(blank=True)

    def __str__(self):
        return "%s @ %s" % (self.template.name, self.creation)


class PdfTag(models.Model):

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=30)

    type = models.CharField(max_length=25, choices=Template.TYPE, blank=True, null=True)

    def __str__(self):
        return "%s" % self.name

    class Meta:
        unique_together = ("tournament", "type")


def get_expire_datetime():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)


def tournament_directory_path(instance, filename):
    return "{0}/{1}".format(instance.tournament.slug, filename)


class Pdf(models.Model):

    file = models.FileField(blank=True, null=True, upload_to=tournament_directory_path)

    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    UPLOAD = "upload"
    MERGE = "merge"
    STATUS = (
        (PROCESSING, "processing"),
        (SUCCESS, "success"),
        (FAILURE, "failure"),
        (ERROR, "error"),
        (UPLOAD, "uploaded"),
        (MERGE, "merged"),
    )

    status = models.CharField(max_length=25, default=PROCESSING, choices=STATUS)

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    task_id = models.CharField(max_length=255, blank=True, null=True)

    name = models.CharField(max_length=255)

    tags = models.ManyToManyField(PdfTag, blank=True)

    rendered_at = models.DateTimeField(auto_now=True)
    expire_at = models.DateTimeField(default=get_expire_datetime)

    invoice_account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.CASCADE
    )

    class Meta:

        unique_together = ("tournament", "name")
        ordering = ["-rendered_at"]

    def __str__(self):
        return "%s" % self.name

    def pure_name(self):
        return self.name.split("/")[-1]


class FileServer(models.Model):
    name = models.CharField(max_length=128, verbose_name="Name")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    hostname = models.CharField(max_length=256, verbose_name="hostname")
    port = models.PositiveIntegerField()
    username = models.CharField(max_length=64, verbose_name="username")
    password = models.CharField(max_length=200, verbose_name="password")
    fingerprint = models.CharField(max_length=4000, default="")

    def __str__(self):
        return self.name
