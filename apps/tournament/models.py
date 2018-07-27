from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Count, Max
from django.template.defaultfilters import slugify
from ordered_model.models import OrderedModel
from unidecode import unidecode

# Create your models here.

class Tournament(models.Model):
    name = models.CharField(max_length=50)
    groups = models.ManyToManyField(Group,blank=True)
    slug = models.SlugField(unique=True)

    allowed_rejections = models.IntegerField(default=3)

    RESULTS_PUBLIC = 'pub'
    RESULTS_PASSWORD = 'pw'
    RESULTS_PERMISSION = 'perm'
    RESULTS_NONE = 'none'
    RESULTS_ACCESS_TYPE = (
        (RESULTS_PUBLIC, 'public'),
        (RESULTS_PASSWORD, 'password'),
        (RESULTS_PERMISSION, 'permission'),
        (RESULTS_NONE, 'none'),
    )

    results_access = models.CharField(max_length=4, choices=RESULTS_ACCESS_TYPE, default=RESULTS_NONE)

    results_password = models.CharField(max_length=128,blank=True,null=True)

    # registration timings

    timezone = models.CharField(max_length=100,blank=True,null=True)

    registration_open = models.DateTimeField(blank=True,null=True)
    registration_close = models.DateTimeField(blank=True,null=True)

    default_templates = models.ManyToManyField("printer.Template", through="printer.DefaultTemplate",related_name="default_templates")

    registration_notifications = models.ManyToManyField("account.Attendee", related_name="registration_notifications", blank=True)

    registration_apply_team = models.BooleanField(default=True)
    registration_apply_newteam = models.BooleanField(default=True)

    registration_teamleaderjurors_required = models.IntegerField(default=1)
    registration_teamleaderjurors_required_guest = models.IntegerField(default=0)

    fee_team = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    bank_default_account = models.ForeignKey('bank.Account', on_delete=models.CASCADE, blank=True, null=True)
    bank_default_due = models.DateTimeField(blank=True, null=True)

    logo = models.ImageField(blank=True, null=True)

    jury_opt_weight_assignmentbalance=models.FloatField(verbose_name="Weight of number of jury assignments", default=1.0)
    jury_opt_weight_expassignmentbalance=models.FloatField(verbose_name="Weight of balance of experienced jurors", default=1.0)
    jury_opt_weight_teamandchairmeettwice=models.FloatField(verbose_name="Weight of team and chair meet twice", default=1.0)
    jury_opt_weight_teamandjurormeetmultiple=models.FloatField(verbose_name="Weight of team and juror meet multiple", default=1.0)
    jury_opt_weight_jurysamecountry=models.FloatField(verbose_name="Weight of multiple jurors from same country", default=1.0)
    jury_opt_weight_bias=models.FloatField(verbose_name="Weight of bias", default=1.0)

    draw_wide = models.BooleanField(default=False)

    def __str__(self):
        return "%s"%(self.name, )

    class Meta:
        permissions = (
            ("app_team", "Access to Team app"),
            ("app_tournament", "Access to Tournament app"),
            ("app_plan", "Access to Plan app"),
            ("app_jury", "Access to Jury app"),
            ("app_fight", "Access to Fight app"),
            ("app_printer", "Access to Printer app"),
            ("app_schedule", "Access to Schedule app"),
            ("app_management", "Access to Management app"),
            ("app_bank", "Access to Bank app"),
            ("app_postoffice", "Access to Postoffice app"),
            ("change_attendee_data", "Customise Participation Data"),
            ("delete_attendee_data", "Delete Participation Data"),
        )

class Problem(models.Model):
    number = models.IntegerField()
    title = models.CharField(max_length=50)
    description = models.TextField()
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("number", "tournament")
        ordering = ["number"]

    def __str__(self):
        return "%d: %s"%(self.number, self.title)

class Origin(models.Model):
    name = models.CharField(max_length=300)
    short = models.CharField(max_length=50, blank=True, null=True)
    alpha2iso = models.CharField(max_length=10, null=True, blank=True)
    slug = models.SlugField()
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    flag = models.ImageField(null=True,blank=True)

    flag_pdf = models.FileField(null=True, blank=True)

    from_registration = models.BooleanField(default=False)

    def __str__(self):
        return "%s"%(self.name,)

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.name))

        if self.flag_pdf:
            fname = self.flag_pdf.name.replace('/', '-')
            self.flag_pdf.name = self.tournament.slug + '/flags/' + fname

        super(Origin, self).save(*args, **kwargs)

    class Meta:
        unique_together = ("slug", "tournament")
        ordering = ("name",)


class Phase(OrderedModel):
    tournament = models.ForeignKey(Tournament,on_delete=models.CASCADE)
    name = models.CharField(max_length=300)
    duration = models.PositiveIntegerField()
    linked = models.BooleanField(default=False)

    order_with_respect_to = "tournament"

class ScheduleTemplate(models.Model):

    name = models.CharField(max_length=250)

    teams = models.IntegerField()

    def teams_nr(self):
        teams = TemplateAttendance.objects.filter(fight__round__template=self).values_list("team").distinct().count()
        return teams

    def __str__(self):
        return "%s : %d Teams" %(self.name, self.teams_nr())

class TemplateRoom(models.Model):
    template = models.ForeignKey(ScheduleTemplate, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def capacity(self):

        cap = self.templatefight_set.annotate(att_count=Count('templateattendance')).aggregate(Max('att_count'))

        return cap['att_count__max']

    def __str__(self):
        return "%s"%self.name

class TemplateRound(models.Model):
    order = models.IntegerField()
    template = models.ForeignKey(ScheduleTemplate,related_name="rounds", on_delete=models.CASCADE)

    class Meta:
        ordering = ['order']

class TemplateFight(models.Model):
    round = models.ForeignKey(TemplateRound, related_name="fights", on_delete=models.CASCADE)
    room = models.ForeignKey(TemplateRoom, on_delete=models.CASCADE)

class TemplateAttendanceDefaultManager(models.Manager):
    def get_queryset(self):
        return super(TemplateAttendanceDefaultManager, self).get_queryset().annotate(
            type_order=models.Case(
                models.When(type="rep", then=0),
                models.When(type="opp", then=1),
                models.When(type="rev", then=2),
                models.When(type="obs", then=3),
                output_field=models.IntegerField(),
            )).order_by('type_order')

class TemplateAttendance(models.Model):
    REP = 'rep'
    OPP = 'opp'
    REV = 'rev'
    OBS = 'obs'
    ROLE_TYPE = (
        (REP, 'Reporter'),
        (OPP, 'Opponent'),
        (REV, 'Reviewer'),
        (OBS, 'Observer'),
    )

    type = models.CharField(max_length=3, choices=ROLE_TYPE)
    team = models.IntegerField()
    fight = models.ForeignKey(TemplateFight, on_delete=models.CASCADE)

    objects = TemplateAttendanceDefaultManager()
