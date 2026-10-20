from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.account.models import ParticipationRole
from apps.registration.validators import role_open
from apps.tournament.models import Tournament


class RoleOpenTests(TestCase):

    def setUp(self):
        self.trn = Tournament.objects.create(name="Test Cup", slug="test-cup")

    def role(self, roletype, deadline):
        return ParticipationRole.objects.create(
            tournament=self.trn,
            name=roletype,
            type=roletype,
            application_deadline=deadline,
        )

    def test_role_without_deadline_is_open(self):
        self.role(ParticipationRole.TEAM_MANAGER, None)
        self.assertTrue(role_open(self.trn, ParticipationRole.TEAM_MANAGER))

    def test_future_deadline_is_open(self):
        self.role(ParticipationRole.TEAM_MANAGER, timezone.now() + timedelta(days=1))
        self.assertTrue(role_open(self.trn, ParticipationRole.TEAM_MANAGER))

    def test_past_deadline_is_closed(self):
        self.role(ParticipationRole.IOC, timezone.now() - timedelta(days=1))
        self.assertFalse(role_open(self.trn, ParticipationRole.IOC))

    def test_missing_role_is_closed(self):
        self.assertFalse(role_open(self.trn, ParticipationRole.VISITOR))

    def test_several_types_open_if_any_is_open(self):
        self.role(ParticipationRole.STUDENT, timezone.now() - timedelta(days=1))
        self.role(ParticipationRole.JUROR, None)
        self.assertTrue(
            role_open(self.trn, ParticipationRole.STUDENT, ParticipationRole.JUROR)
        )

    def test_other_tournament_does_not_open_a_role(self):
        other = Tournament.objects.create(name="Other Cup", slug="other-cup")
        ParticipationRole.objects.create(
            tournament=other, name="Team Manager", type=ParticipationRole.TEAM_MANAGER
        )
        self.assertFalse(role_open(self.trn, ParticipationRole.TEAM_MANAGER))

