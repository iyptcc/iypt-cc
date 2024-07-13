from django.db import models
from django.utils.functional import cached_property
from django_celery_results.models import TaskResult
from ordered_model.models import OrderedModel

from apps.account.models import ActiveUser, Attendee
from apps.fight.models import ScanProcessing
from apps.plan.models import Fight, FightRole, Round, Stage, StageAttendance
from apps.tournament.models import Origin, Tournament

# Create your models here.


class JurorAvailabilityGroup(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Juror(models.Model):
    attendee = models.OneToOneField(Attendee, on_delete=models.CASCADE)
    fights = models.ManyToManyField(Fight, through="JurorSession")

    conflicting = models.ManyToManyField(Origin, blank=True)

    local = models.BooleanField(null=True, blank=True)

    possible_chair = models.BooleanField(default=False, null=True, blank=True)

    EXPERIENCE_NEW = -1
    EXPERIENCE_LOW = 0
    EXPERIENCE_HIGH = 1
    EXPERIENCES = (
        (EXPERIENCE_NEW, "no experience"),
        (EXPERIENCE_LOW, "low experience"),
        (EXPERIENCE_HIGH, "high experience"),
    )
    experience = models.IntegerField(default=EXPERIENCE_LOW, choices=EXPERIENCES)

    availability = models.ManyToManyField(Round, blank=True)

    bias = models.FloatField(default=0)

    notice = models.TextField(null=True, blank=True)

    max_assign = models.IntegerField(null=True, blank=True)
    max_chair = models.IntegerField(null=True, blank=True)

    availability_group = models.ForeignKey(
        JurorAvailabilityGroup, on_delete=models.SET_NULL, blank=True, null=True
    )

    def __str__(self):
        return "%s" % (self.attendee,)

    def assignments(self):

        used = []

        assigned_rounds = self.fights.values_list("round__order", flat=True)
        available_rounds = self.availability.values_list("order", flat=True)

        # print(assigned_rounds)
        # print(available_rounds)

        for round in self.attendee.tournament.round_set(manager="selectives").all():
            if round.order in assigned_rounds:
                typ = self.jurorsession_set.get(
                    fight__round__order=round.order
                ).role.type
                if typ == JurorRole.CHAIR:
                    used.append("chair")
                elif typ == JurorRole.JUROR:
                    used.append("used")
                else:
                    used.append("nonvoting")
            elif round.order in available_rounds:
                used.append("free")
            else:
                used.append("na")

        return used

    @cached_property
    def conflicting_ids_cached(self):
        return list(self.conflicting.all().values_list("id", flat=True))

    class Meta:
        permissions = (
            # ("view_juror", "Can list all jurors and jury plans"),
            ("clock", "Can view clock"),
            ("clocks", "Can view all clocks"),
            ("publish_fights", "Can publish fights and previews"),
            ("stats", "Can view statistics of jurors"),
        )
        ordering = ["attendee__active_user__user__last_name"]


class JurorOccupation(OrderedModel):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    order_with_respect_to = "tournament"

    def __str__(self):
        return "%s" % self.name


class PossibleJuror(models.Model):
    person = models.ForeignKey(ActiveUser, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    experience = models.IntegerField(
        default=Juror.EXPERIENCE_LOW, choices=Juror.EXPERIENCES
    )
    occupation = models.ForeignKey(
        JurorOccupation, on_delete=models.SET_NULL, blank=True, null=True
    )
    remark = models.CharField(max_length=1000, blank=True, null=True)

    approved_by = models.ForeignKey(
        ActiveUser,
        related_name="approved_possiblejurors",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    approved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("person", "tournament")


class JurorRole(models.Model):

    JUROR = "1ju"
    CHAIR = "0ch"
    NONVOTING = "2nv"
    ROLE_TYPE = (
        (CHAIR, "Chair"),
        (JUROR, "Juror"),
        (NONVOTING, "Non-Voting"),
    )
    type = models.CharField(max_length=3, choices=ROLE_TYPE, null=True, blank=True)

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    class Meta:
        ordering = ["type"]

    def __str__(self):
        return "%s" % (self.name)


class JurorSessionManager(models.Manager):
    def get_queryset(self):
        return (
            super(JurorSessionManager, self)
            .get_queryset()
            .filter(role__type=JurorRole.JUROR)
            .order_by("juror")
        )


class ChairSessionManager(models.Manager):
    def get_queryset(self):
        return (
            super(ChairSessionManager, self)
            .get_queryset()
            .filter(role__type=JurorRole.CHAIR)
        )


class VotingSessionManager(models.Manager):
    def get_queryset(self):
        return (
            super(VotingSessionManager, self)
            .get_queryset()
            .filter(role__type__in=[JurorRole.JUROR, JurorRole.CHAIR])
            .order_by("role__type", "juror")
        )


class NonVotingSessionManager(models.Manager):
    def get_queryset(self):
        return (
            super(NonVotingSessionManager, self)
            .get_queryset()
            .filter(role__type__in=[JurorRole.NONVOTING])
        )


class JurorSession(models.Model):
    juror = models.ForeignKey(Juror, on_delete=models.CASCADE)
    fight = models.ForeignKey(Fight, on_delete=models.CASCADE)

    role = models.ForeignKey(JurorRole, on_delete=models.CASCADE)

    grades = models.ManyToManyField(StageAttendance, through="JurorGrade", blank=True)

    objects = models.Manager()

    order = models.IntegerField(null=True, blank=True)

    jurors = JurorSessionManager()
    chair = ChairSessionManager()
    voting = VotingSessionManager()
    nonvoting = NonVotingSessionManager()

    def __str__(self):
        return "%s in %s as %s" % (self.juror, self.fight, self.role)

    class Meta:
        permissions = (
            ("change_all_jurorsessions", "Can change jury any time"),
            ("assign_jurors", "Can assign jurors to fights"),
            ("delete_all_jurorsessions", "Delete all juror sessions together"),
        )
        unique_together = ("order", "fight")
        # ordering = ['order']
        ordering = ["role__type", "juror"]


class JurorGrade(models.Model):
    juror_session = models.ForeignKey(JurorSession, on_delete=models.CASCADE)
    stage_attendee = models.ForeignKey(StageAttendance, on_delete=models.CASCADE)

    grade = models.FloatField()

    valid = models.BooleanField(default=False)

    def __str__(self):
        return "%s graded %s: %f (%s)" % (
            self.juror_session.juror,
            self.stage_attendee,
            self.grade,
            self.valid,
        )

    @property
    def public_grade(self):
        if self.valid and self.juror_session.role.type in [
            JurorRole.JUROR,
            JurorRole.CHAIR,
        ]:
            return self.grade
        else:
            return None

    class Meta:
        permissions = (
            ("view_results", "View published results"),
            ("validate_grades", "Validate grades after manual check"),
            ("grade_dump", "Dump grades and results"),
            ("member_rank", "List Ranking of Team Members"),
        )


class AssignResult(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=255)

    author = models.ForeignKey(
        Attendee, blank=True, null=True, on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    finished = models.DateTimeField(null=True, blank=True)

    total_rounds = models.IntegerField()
    room_jurors = models.IntegerField()
    cooling_base = models.FloatField()
    fix_rounds = models.IntegerField(default=0)


def dir_path_generic(fieldstr, instance, filename):
    if hasattr(instance, "stage"):
        return (
            "grading/%d-%d/%s-"
            % (instance.jurorsession_id, instance.stage_id, fieldstr)
            + filename
        )
    else:
        return "grading/unknown/%s-" % fieldstr + filename


def dir_path_header(instance, filename):
    return dir_path_generic("header", instance, filename)


def dir_path_rep(instance, filename):
    return dir_path_generic("rep", instance, filename)


def dir_path_opp(instance, filename):
    return dir_path_generic("opp", instance, filename)


def dir_path_rev(instance, filename):
    return dir_path_generic("rev", instance, filename)


def dir_path_full(instance, filename):
    return dir_path_generic("full", instance, filename)


class GradingSheet(models.Model):

    jurorsession = models.ForeignKey(JurorSession, on_delete=models.CASCADE)
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE)

    header = models.ImageField(blank=True, null=True, upload_to=dir_path_header)
    rep = models.ImageField(blank=True, null=True, upload_to=dir_path_rep)
    opp = models.ImageField(blank=True, null=True, upload_to=dir_path_opp)
    rev = models.ImageField(blank=True, null=True, upload_to=dir_path_rev)
    full = models.ImageField(blank=True, null=True, upload_to=dir_path_full)

    process_job = models.ForeignKey(
        ScanProcessing, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return "%s %s" % (self.jurorsession.juror, self.stage)


class GradingGroup(OrderedModel):
    role = models.ForeignKey(FightRole, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    minimum = models.FloatField()
    maximum = models.FloatField()

    def __str__(self):
        return "%s for %s (min %s max %s)" % (
            self.name,
            self.role,
            self.minimum,
            self.maximum,
        )


class GroupGrade(models.Model):
    value = models.FloatField()
    group = models.ForeignKey(GradingGroup, on_delete=models.CASCADE)
    juror_session = models.ForeignKey(JurorSession, on_delete=models.CASCADE)
    stage_attendee = models.ForeignKey(StageAttendance, on_delete=models.CASCADE)


class GradingCategory(OrderedModel):
    group = models.ForeignKey(GradingGroup, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    def __str__(self):
        return "%s of %s" % (self.title, self.group.name)


class CategoryGrade(models.Model):
    value = models.FloatField()
    category = models.ForeignKey(GradingCategory, on_delete=models.CASCADE)
    juror_session = models.ForeignKey(JurorSession, on_delete=models.CASCADE)


class GradingElement(models.Model):
    category = models.ForeignKey(GradingCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000)
    start = models.FloatField()
    end = models.FloatField()

    def __str__(self):
        return "%s to %s: %s in %s" % (
            self.start,
            self.end,
            self.name,
            self.category.title,
        )
