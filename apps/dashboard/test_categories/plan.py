import random

from apps.account.models import ParticipationRole
from apps.plan.models import Round
from apps.result.utils import _ranking
from apps.tournament.models import ScheduleTemplate, Tournament

from .verbose_testcase import VerboseTestCase


class PlanTests(VerboseTestCase):

    def generate_placeholders(self):
        r = self.client.post("/plan/placeholder/teams/generate")
        self.assertIn(r.status_code, [302, 200])

    def load_schedule(self, team_nr):
        s = ScheduleTemplate.objects.get(teams=team_nr, name="AYPT schedule")
        par = {}
        roomname = "A"
        for r in s.templateroom_set.all():
            par["room-%d" % r.id] = roomname
            roomname = chr(ord(roomname) + 1)
        self._preview_post("/plan/placeholder/plan/load/%d" % s.id, par)

    def assign_random_placeholders(self):

        trn = self.user.profile.tournament
        phs = trn.teamplaceholder_set.all().values_list("id", flat=True)
        t = list(trn.team_set.all().values_list("id", flat=True))
        random.shuffle(t)

        print(phs)
        print(t)

        post = {}
        for idx, ph in enumerate(phs):
            post["phteam-%d" % ph] = t[idx]

        r = self.client.post("/plan/placeholder/teams", post)
        self.assertIn(r.status_code, [302, 200])

    def apply_teams(self):

        r = self.client.post("/plan/placeholder/plan/apply")
        print(r.status_code)
        print(r)
        self.assertIn(r.status_code, [302, 200])

    def create_jurors(
        self,
    ):

        leaderids = self.user.profile.tournament.attendee_set.filter(
            roles__type__in=[ParticipationRole.TEAM_LEADER, ParticipationRole.JUROR]
        ).values_list("id", flat=True)

        self._preview_post(
            "/plan/persons",
            {"_juror": "create Jurors of selected", "persons": leaderids},
            {"action": "_juror"},
        )

    def get_attendees(self):
        a = self.user.profile.tournament.attendee_set.all()
        for att in a:
            print(
                att, att.roles.all(), att.teammember_set.values_list("team", flat=True)
            )

    def create_final(self, trns):

        data = {}

        rounds = Round.selectives.filter(tournament__slug=trns).order_by("order")
        rank = _ranking(rounds, use_cache=False, internal=True)
        r = 1
        for team in rank[-1]:
            if team["rank"] <= 3:
                data["team-%d" % team["pk"]] = r  # team['rank']
                r += 1

        self._preview_post("/plan/final", data)
