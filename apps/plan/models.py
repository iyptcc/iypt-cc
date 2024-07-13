from decimal import Decimal

from django.db import models
from django.template.defaultfilters import slugify
from django.utils.functional import cached_property

from apps.account.models import Attendee
from apps.printer.models import Pdf
from apps.team.models import Team, TeamMember
from apps.tournament.models import Problem, Tournament
from apps.virtual.models import BBBInstance

# Create your models here.


class Room(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    location = models.CharField(max_length=150)
    slug = models.SlugField()

    def __str__(self):
        return "%s @ %s in %s" % (self.name, self.location, self.tournament)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Room, self).save(*args, **kwargs)


class SelectiveRoundManager(models.Manager):
    def get_queryset(self):
        return (
            super(SelectiveRoundManager, self)
            .get_queryset()
            .filter(type=Round.SELECTIVE)
        )


class FinalRoundManager(models.Manager):
    def get_queryset(self):
        return super(FinalRoundManager, self).get_queryset().filter(type=Round.FINAL)


class Round(models.Model):
    SELECTIVE = "s"
    FINAL = "f"
    ROUND_TYPE = (
        (SELECTIVE, "selective PF"),
        (FINAL, "final PF"),
    )
    order = models.IntegerField()
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    objects = models.Manager()

    selectives = SelectiveRoundManager()
    finals = FinalRoundManager()

    publish_ranking = models.BooleanField(default=False)
    publish_schedule = models.BooleanField(default=False)
    publish_jurors = models.BooleanField(default=False)

    preview_fixed_problem = models.BooleanField(default=False)

    pdf_juryplan = models.ForeignKey(
        Pdf, on_delete=models.SET_NULL, blank=True, null=True, related_name="jury_round"
    )
    pdf_teamplan = models.ForeignKey(
        Pdf, on_delete=models.SET_NULL, blank=True, null=True, related_name="team_round"
    )
    pdf_ranking = models.ForeignKey(
        Pdf, on_delete=models.SET_NULL, blank=True, null=True, related_name="ranking"
    )
    pdf_problem_select = models.ForeignKey(
        Pdf,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="problem_select",
    )

    feedback_task_id = models.CharField(max_length=255, blank=True, null=True)
    grading_task_id = models.CharField(max_length=255, blank=True, null=True)

    feedback_locked = models.BooleanField(default=False)

    currently_active = models.BooleanField(default=False)

    review_phase = models.BooleanField(default=True)

    reserved_jurors = models.ManyToManyField("jury.Juror")

    type = models.CharField(
        max_length=1,
        choices=ROUND_TYPE,
        default=SELECTIVE,
    )

    def __str__(self):
        return "Round %d in %s" % (self.order, self.tournament)

    class Meta:
        ordering = ["order"]
        unique_together = ("order", "tournament")

        permissions = (
            ("apply_schedule", "Apply a schedule to real teams"),
            ("import_curiie", "Import Curiie Data"),
            ("view_plan", "View plan"),
        )


class Fight(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)

    operators = models.ManyToManyField(Attendee, blank=True)
    locked = models.BooleanField(default=True)

    publish_grades = models.BooleanField(default=False)
    publish_preview = models.BooleanField(default=False)
    publish_partials = models.BooleanField(default=False)
    publish_slides = models.BooleanField(default=False)

    pdf_preview = models.ForeignKey(
        Pdf, on_delete=models.SET_NULL, blank=True, null=True
    )
    pdf_result = models.ForeignKey(
        Pdf,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="result_fight",
    )
    pdf_partial_grades = models.ForeignKey(
        Pdf,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="fight_partial",
    )

    pdf_jury_feedback = models.ForeignKey(
        Pdf,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="jury_feedback",
    )
    pdf_grade_overview = models.ForeignKey(
        Pdf,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="grade_overview",
    )

    virtual_server = models.ForeignKey(
        BBBInstance, on_delete=models.SET_NULL, blank=True, null=True
    )
    virtual_attendees = models.ManyToManyField(
        Attendee, blank=True, related_name="virtual_rooms"
    )
    virtual_guests = models.ManyToManyField("virtual.BBBGuest", blank=True)
    virtual_record = models.BooleanField(default=False)

    @cached_property
    def origin_ids_cached(self):
        return list(
            self.stage_set.get(order=1)
            .attendees.all()
            .values_list("origin_id", flat=True)
        )

    @property
    def chat_name(self):
        return "fight-%d-%s" % (self.round.order, slugify(self.room.name))

    def __str__(self):
        return "Round %s, %s" % (self.round.order, self.room.name)

    class Meta:
        permissions = (
            ("view_fight_operator", "Can list fight operators/locks"),
            ("change_fight_operator", "Can change fight operators/locks"),
            ("publish_fights", "Can publish fights"),
            ("delete_final", "Delete Final"),
            ("change_final", "Change Final"),
        )
        ordering = ["room__name"]


class TeamPlaceholder(models.Model):
    name = models.CharField(max_length=50)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    team = models.OneToOneField(Team, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        if self.team:
            return "%s (%s)" % (self.name, self.team.origin.name)

        return "%s" % (self.name)

    class Meta:
        permissions = (
            ("assign_placeholders", "Assign Teams to placeholders"),
            ("view_placeholders", "View Teamplaceholders"),
        )


class Event(models.Model):

    name = models.CharField(max_length=1000)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    round = models.OneToOneField(
        Round, blank=True, null=True, on_delete=models.SET_NULL
    )

    time_start = models.DateTimeField(blank=True, null=True)
    time_end = models.DateTimeField(blank=True, null=True)

    public = models.BooleanField(default=False)

    SELECTIVE = "selective"
    FINAL = "final"
    OPENING = "opening"
    CLOSING = "closing"
    ROUND_TYPE = (
        (SELECTIVE, "selective PF"),
        (FINAL, "final PF"),
        (OPENING, "opening ceremony"),
        (CLOSING, "closing ceremony"),
    )

    type = models.CharField(max_length=30, choices=ROUND_TYPE, null=True, blank=True)

    def __str__(self):
        return "Event %s in %s" % (self.name, self.tournament)

    class Meta:
        ordering = ["time_start"]
        unique_together = ("name", "tournament")


def dir_presentation_path(instance, filename):
    return f"{instance.fight.round.tournament.slug}_slides/round_{instance.fight.round.order}/{instance.rep_attendance.team.origin.slug}.pdf"


class Stage(models.Model):
    order = models.IntegerField()
    fight = models.ForeignKey(Fight, on_delete=models.CASCADE)
    presented = models.ForeignKey(
        Problem,
        related_name="presented_in",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    rejections = models.ManyToManyField(Problem, blank=True)

    attendees = models.ManyToManyField(Team, through="StageAttendance")

    jurors_grading = models.BooleanField(default=False)

    pdf_grading_sheets = models.ForeignKey(
        Pdf, on_delete=models.SET_NULL, blank=True, null=True
    )

    pdf_presentation = models.FileField(
        blank=True, null=True, upload_to=dir_presentation_path
    )

    def __str__(self):
        return "Stage %d in %s" % (self.order, self.fight)

    class Meta:
        ordering = ["order"]

    @cached_property
    def rep_role(self):
        return self.fight.round.tournament.fightrole_set.get(type=FightRole.REP)

    @cached_property
    def opp_role(self):
        return self.fight.round.tournament.fightrole_set.get(type=FightRole.OPP)

    @cached_property
    def rev_role(self):
        return self.fight.round.tournament.fightrole_set.get(type=FightRole.REV)

    @cached_property
    def obs_role(self):
        return self.fight.round.tournament.fightrole_set.get(type=FightRole.OBS)

    @cached_property
    def rep_attendance(self):
        return self.stageattendance_set.get(role__type=FightRole.REP)

    @cached_property
    def opp_attendance(self):
        return self.stageattendance_set.get(role__type=FightRole.OPP)

    @cached_property
    def rev_attendance(self):
        return self.stageattendance_set.get(role__type=FightRole.REV)

    @cached_property
    def obs_attendance(self):
        try:
            return self.stageattendance_set.get(role__type=FightRole.OBS)
        except:
            return None

    @cached_property
    def rep_attendance_grades(self):
        return (
            self.stageattendance_set.select_related("team__origin", "role")
            .prefetch_related("stage__rejections")
            .get(role__type=FightRole.REP)
        )

    @cached_property
    def opp_attendance_grades(self):
        return (
            self.stageattendance_set.select_related("team__origin", "role")
            .prefetch_related("stage__rejections")
            .get(role__type=FightRole.OPP)
        )

    @cached_property
    def rev_attendance_grades(self):
        return (
            self.stageattendance_set.select_related("team__origin", "role")
            .prefetch_related("stage__rejections")
            .get(role__type=FightRole.REV)
        )

    @cached_property
    def reporter(self):
        if self.rep_attendance.active_person:
            return self.rep_attendance.active_person.attendee

    @cached_property
    def opponent(self):
        if self.opp_attendance.active_person:
            return self.opp_attendance.active_person.attendee

    @cached_property
    def reviewer(self):
        if self.rev_attendance.active_person:
            return self.rev_attendance.active_person.attendee


class FightRoleDefaultManager(models.Manager):
    def get_queryset(self):
        return (
            super(FightRoleDefaultManager, self)
            .get_queryset()
            .annotate(
                type_order=models.Case(
                    models.When(type="rep", then=0),
                    models.When(type="opp", then=1),
                    models.When(type="rev", then=2),
                    models.When(type="obs", then=3),
                    output_field=models.IntegerField(),
                )
            )
            .order_by("type_order")
        )


class FightRole(models.Model):
    REP = "rep"
    OPP = "opp"
    REV = "rev"
    OBS = "obs"
    ROLE_TYPE = (
        (REP, "Reporter"),
        (OPP, "Opponent"),
        (REV, "Reviewer"),
        (OBS, "Observer"),
    )

    name = models.CharField(max_length=50)
    factor = models.FloatField()
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    type = models.CharField(
        max_length=3,
        choices=ROLE_TYPE,
        null=True,
        blank=True,
    )

    objects = FightRoleDefaultManager()

    def __str__(self):
        return "%s : %.1f" % (self.name, self.factor)


class StageAttendanceDefaultManager(models.Manager):
    def get_queryset(self):
        return (
            super(StageAttendanceDefaultManager, self)
            .get_queryset()
            .annotate(
                type_order=models.Case(
                    models.When(role__type="rep", then=0),
                    models.When(role__type="opp", then=1),
                    models.When(role__type="rev", then=2),
                    models.When(role__type="obs", then=3),
                    output_field=models.IntegerField(),
                )
            )
            .order_by("type_order")
        )


class StageAttendance(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, blank=True, null=True, on_delete=models.CASCADE)
    team_placeholder = models.ForeignKey(
        TeamPlaceholder, blank=True, null=True, on_delete=models.CASCADE
    )

    role = models.ForeignKey(FightRole, on_delete=models.CASCADE)

    active_person = models.ForeignKey(
        TeamMember, blank=True, null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return "team %s/%s in %s as %s" % (
            self.team,
            self.team_placeholder,
            self.stage,
            self.role,
        )

    objects = StageAttendanceDefaultManager()

    def average(self, only_valid=True):
        grades = []
        if only_valid:
            for g in self.jurorgrade_set.exclude(
                juror_session__role__type="2nv"
            ).filter(valid=True):
                grades.append(Decimal(int(g.grade)))
        else:
            for g in self.jurorgrade_set.exclude(juror_session__role__type="2nv"):
                grades.append(Decimal(int(g.grade)))

        if len(grades) >= 3:
            best = max(grades)
            worst = min(grades)

            grades.remove(best)
            grades.remove(worst)

            grades.append((best + worst) / Decimal("2"))

            return sum(grades) / len(grades)
        elif len(grades) > 0:
            return sum(grades) / len(grades)
        else:
            return None

    @cached_property
    def grade_average(self):
        return self.average()

    @property
    def prelim_average(self):
        return self.average(False)
