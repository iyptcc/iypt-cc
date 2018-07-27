import datetime

from django.db import models
from django.db.models import Q

from apps.bank.models import Account
from apps.tournament.models import Tournament

# Create your models here.

class Template(models.Model):
    name = models.CharField(max_length=200)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, blank=True, default=None, on_delete=models.CASCADE)

    PREVIEW = "preview"
    RANKING = "ranking"
    RESULTS = "results"
    JURYROUND = "jury_round"
    TEAMROUND = "team_round"
    JURYFEEDBACK = "jury_feedback"
    PROBLEMSELECT = "problem_select"
    PERSONS = "persons"
    REGISTRATION = "registration"
    INVOICE = "invoice"
    TYPE = (
        (PREVIEW, 'Preview'),
        (RANKING, 'Ranking'),
        (RESULTS, 'Results'),
        (JURYROUND, 'Jury Round Plan'),
        (TEAMROUND, 'Team Round Plan'),
        (JURYFEEDBACK, 'Jury Fight Feedback'),
        (PROBLEMSELECT, 'Problem Selection for last PF'),
        (PERSONS, 'Persons'),
        (REGISTRATION, 'Registration'),
        (INVOICE, 'Invoice'),
    )

    type = models.CharField(max_length=25, choices=TYPE, blank=True, null=True)

    files = models.ManyToManyField("printer.Pdf", blank=True)

    def all_files(self):
        f = self.files.all()
        if self.parent:
            f |= self.parent.all_files()
        return f

    def __str__(self):
        return "%s"%self.name

class DefaultTemplate(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, related_name="default_template", on_delete=models.CASCADE)

    type = models.CharField(max_length=25, choices=Template.TYPE)

    class Meta:
        unique_together = ("tournament", "type")

class TemplateVersion(models.Model):

    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    creation = models.DateTimeField(auto_now=True)
    author = models.ForeignKey("account.ActiveUser", on_delete=models.CASCADE)

    src = models.TextField(blank=True)

    def __str__(self):
        return "%s @ %s"%(self.template.name, self.creation)


class PdfTag(models.Model):

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=30)

    type = models.CharField(max_length=25, choices=Template.TYPE, blank=True, null=True)

    def __str__(self):
        return "%s"%self.name

    class Meta:
        unique_together = ("tournament", "type")

def get_expire_datetime():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)

class Pdf(models.Model):

    file = models.FileField(blank=True, null=True)

    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    UPLOAD = "upload"
    STATUS = (
        (PROCESSING, 'processing'),
        (SUCCESS, 'success'),
        (FAILURE, 'failure'),
        (ERROR, 'error'),
        (UPLOAD, 'uploaded'),
    )

    status = models.CharField(max_length=25, default=PROCESSING, choices=STATUS)

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    task_id = models.CharField(max_length=255, blank=True, null=True)

    name = models.CharField(max_length=255)

    tags = models.ManyToManyField(PdfTag, blank=True)

    rendered_at = models.DateTimeField(auto_now=True)
    expire_at = models.DateTimeField(default=get_expire_datetime)

    invoice_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:

        unique_together = ("tournament","name")
        ordering = ["-rendered_at"]

    def __str__(self):
        return "%s"%self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            name = self.name.replace('/','-')
            self.name = self.tournament.slug + '/' + name
            if self.file:
                fname = self.file.name.replace('/', '-')
                self.file.name = self.tournament.slug + '/' + fname
        super(Pdf,self).save(*args, **kwargs)

    def pure_name(self):
        return self.name.split('/')[-1]
