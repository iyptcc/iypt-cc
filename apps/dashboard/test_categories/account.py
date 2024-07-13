from django.contrib.auth.models import User

from .verbose_testcase import VerboseTestCase


class AccountTests(VerboseTestCase):

    def set_active_tournament(self, t_slug):
        att = self.user.profile.attendee_set.get(tournament__slug=t_slug)
        r = self.client.post("/account/tournament/", {"active": att.id})
        self.assertIn(r.status_code, [302, 200])
        self.user = User.objects.get(id=self.user.id)
        self.assertEqual(self.user.profile.active, att)
