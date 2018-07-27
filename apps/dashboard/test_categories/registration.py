from random import randint

from django.contrib.auth.hashers import check_password

from apps.account.models import Attendee
from apps.registration.models import Application
from apps.team.models import Team, TeamRole

from .verbose_testcase import VerboseTestCase


class RegistrationTests(VerboseTestCase):

    def apply_new_team(self,trn,name):
        self._preview_post("/registration/%s/team/"%trn,
                           {"new_name": name, "_newteam": "apply"}, {"action": "_new_name"})
        #r = self.client.post("/registration/%s/team/"%trn, {"new_name": name, "_newteam": "apply"})
        #self.assertIn(r.status_code, [302, 200])

    def accept_new_team(self, appl_obj):
        r = self.client.post("/registration/accept/team/%d/"%appl_obj.id,
                             {"origin":appl_obj.origin.name,"leader":appl_obj.applicant.id, "competing":"on"})
        self.assertIn(r.status_code, [302, 200])

    def set_team_password(self, team, pw):
        r = self.client.post("/registration/manage/team/%s/"%team,
                             {"join_password":pw,'notify_applications':True})
        self.assertIn(r.status_code, [302, 200])

        team = Team.objects.get(tournament=self.user.profile.tournament,origin__slug=team)
        self.assertTrue(check_password(pw,team.join_password))

    def apply_as_member(self,t_slug, team,pw, role=TeamRole.MEMBER):
        team = Team.objects.get(tournament__slug=t_slug,origin__slug=team)
        self._preview_post("/registration/%s/member/" % t_slug, {"team":team.id, "password":pw,"role":team.tournament.teamrole_set.get(type=role).id})
        #self.assertIn(r.status_code, [302, 200])
        #print(Application.objects.all())

    def accept_team_member(self,appl):
        act_user_id = appl.applicant_id
        trn = appl.tournament
        team = appl.team
        r = self.client.post("/registration/manage/team/%s/accept/%d/"%(appl.team.origin.slug,appl.id),{"role":appl.team_role.id})
        self.assertIn(r.status_code, [302, 200])

        Attendee.objects.get(active_user_id=act_user_id, tournament=trn).team_set.get(id=team.id)

    def set_team_role(self,tm,role, manager=False):
        args = {"role":tm.team.tournament.teamrole_set.get(type=role).id}
        if manager:
            args.update({"manager": "on"})
        r = self.client.post("/registration/manage/team/%s/edit/%d/"%(tm.team.origin.slug,tm.id), args )
        self.assertIn(r.status_code, [302, 200])

    def apply_possible_juror(self,tournament,experience=None):
        if experience == None:
            experience = randint(-1,1)
        self._preview_post("/registration/%s/jurors/apply"%tournament,{"experience":experience})
