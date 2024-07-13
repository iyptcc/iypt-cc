from django.db import models
from django.db.models import Q

from apps.account.models import Attendee, ParticipationRole
from apps.tournament.models import Origin, Problem, Tournament

# Create your models here.


class TeamRole(models.Model):

    CAPTAIN = "captain"
    MEMBER = "member"
    LEADER = "leader"
    ASSOCIATED = "associated"
    ROLE_TYPE = (
        (CAPTAIN, "Captain"),
        (MEMBER, "Member"),
        (LEADER, "Leader"),
        (ASSOCIATED, "Associated"),
    )

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    type = models.CharField(max_length=15, choices=ROLE_TYPE, null=True, blank=True)

    participation_roles = models.ManyToManyField(ParticipationRole, blank=True)

    members_min = models.PositiveSmallIntegerField(blank=True, null=True)
    members_max = models.PositiveSmallIntegerField(blank=True, null=True)

    def __str__(self):
        return "%s" % (self.name,)


class CompetingTeamManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_competing=True)


class Team(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    members = models.ManyToManyField(Attendee, through="TeamMember")
    origin = models.ForeignKey(Origin, on_delete=models.CASCADE)

    join_password = models.CharField(max_length=128, blank=True, null=True)
    notify_applications = models.BooleanField(
        default=True, verbose_name="Notify Managers by Email for new Applications"
    )

    is_competing = models.BooleanField(default=True)

    objects = models.Manager()

    competing = CompetingTeamManager()

    aypt_prepared_problems = models.ManyToManyField(Problem)

    storage_link = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        permissions = (("view_teams", "Can list all team details"),)
        ordering = ["origin__name"]

    def __str__(self):
        nc = ""
        if not self.is_competing:
            nc = " n comp."
        return "%s%s" % (self.origin.name, nc)

    def get_students(self):
        return self.members.filter(
            Q(teammember__role__type=TeamRole.CAPTAIN)
            | Q(teammember__role__type=TeamRole.MEMBER)
        ).prefetch_related("active_user__user")

    def get_leaders(self):
        return self.members.filter(
            teammember__role__type=TeamRole.LEADER
        ).prefetch_related("active_user__user")

    def get_associated(self):
        return self.members.filter(
            teammember__role__type=TeamRole.ASSOCIATED
        ).prefetch_related("active_user__user")

    def get_managers(self):
        return self.members.filter(teammember__manager=True).prefetch_related(
            "active_user__user"
        )


class StudentMemberManager(models.Manager):
    def get_queryset(self):
        return (
            super(StudentMemberManager, self)
            .get_queryset()
            .filter(Q(role__type=TeamRole.MEMBER) | Q(role__type=TeamRole.CAPTAIN))
        )


class TeamMember(models.Model):
    attendee = models.ForeignKey(Attendee, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    role = models.ForeignKey(TeamRole, on_delete=models.CASCADE)

    manager = models.BooleanField(default=False)

    objects = models.Manager()

    students = StudentMemberManager()

    def __str__(self):
        return "%s" % (self.attendee.full_name)

    class Meta:
        unique_together = ("attendee", "team")
