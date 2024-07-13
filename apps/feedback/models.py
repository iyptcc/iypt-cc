from django.db import models

from apps.jury.models import JurorSession
from apps.team.models import Team
from apps.tournament.models import Tournament


class FeedbackGrade(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    name = models.CharField(max_length=50)
    value = models.FloatField()

    class Meta:
        unique_together = ("tournament", "value")

    def __str__(self):
        return self.name


class Feedback(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    jurorsession = models.ForeignKey(JurorSession, on_delete=models.CASCADE)

    grade = models.ForeignKey(FeedbackGrade, on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)

    class Meta:
        permissions = (
            ("change_all_feedback", "Can change any feedback"),
            ("stats", "Can see feedback statistics"),
        )

    def __str__(self):
        return "%s for %s:%s" % (self.team, self.jurorsession, self.grade)


class ChairFeedbackCriterion(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)


class ChairFeedback(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    jurorsession = models.ForeignKey(JurorSession, on_delete=models.CASCADE)

    grades = models.ManyToManyField(
        ChairFeedbackCriterion, through="ChairFeedbackGrade"
    )
    comment = models.TextField(null=True, blank=True)


class ChairFeedbackGrade(models.Model):
    feedback = models.ForeignKey(ChairFeedback, on_delete=models.CASCADE)
    criterion = models.ForeignKey(ChairFeedbackCriterion, on_delete=models.CASCADE)

    grade = models.ForeignKey(FeedbackGrade, on_delete=models.CASCADE)
