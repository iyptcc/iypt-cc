
import datetime
import os
from glob import glob

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils import timezone

from apps.jury.models import PossibleJuror
from apps.registration.models import Application, AttendeeProperty, UserProperty
from apps.schedule.utils import import_template
from apps.team.models import TeamMember, TeamRole

from .test_categories import account, fakedata, jury, management, plan, registration, tournament
from .test_categories.utils import Log
from .test_categories.verbose_testcase import VerboseTestCase


class FullTournament(VerboseTestCase):

    def runTest(self):
        self.setup_plans()
        self.test_full()
        #self.test_individual()

    def setup_plans(self):
        for f in glob(os.path.join(settings.BASE_DIR, 'data', 'templates', '*')):
            import_template(f)

    def setup_permissions(self):
        root_account = account.AccountTests("root")

        root_account.set_active_tournament("test-iypt")

        root_tournament = tournament.TournamentTests(username="root")

        root_tournament.create_perm_group("admin-group",
                                          ["tournament.app_tournament", "tournament.app_plan", "plan.view_plan",
                                           "auth.add_group", "auth.change_group", "account.view_all_persons",
                                           "tournament.change_tournament", "registration.manage_data",
                                           "registration.manage_team", "registration.accept_team",
                                           "account.add_participationrole", "account.change_participationrole",
                                           "account.delete_participationrole", "tournament.add_problem",'tournament.change_attendee_data',"tournament.app_jury",
                                           "registration.accept_juror",'plan.add_teamplaceholder' ])

        root_tournament.add_groups_to_persons(['admin-group'], ["admin"])

        Log.step("Tournament Admin preparation")

        admin_account = account.AccountTests("admin")

        admin_account.set_active_tournament("test-iypt")

        admin_tournament = tournament.TournamentTests("admin")
        admin_tournament.tournament_settings(timezone.now() - datetime.timedelta(days=2),
                                             timezone.now() + datetime.timedelta(days=2))

        Log.step("Create Permission Groups")

        admin_tournament.create_perm_group("tl-group", ["registration.manage_team"])
        admin_tournament.create_perm_group("participant-group", ["registration.manage_data"])

        admin_tournament.add_groups_to_role(["tl-group", "participant-group"], "tl")
        admin_tournament.add_groups_to_role(["participant-group"], "st")

    def test_full(self):

        trn = fakedata.FakeTournament('en_GB', 7, 5, 10, 15)

        Log.step("Bootstrapping")

        root_mgnt = management.ManagementTests("root")

        root_mgnt.create_tournament("Test IYPT", "test-iypt")

        root_mgnt.create_user(username="admin", email="iypt-admin@x.xx", first_name="The", last_name="Admin")

        for t in UserProperty.TYPE_CHOICES:
            root_mgnt.add_profile_property("profile data-"+t[1],t[0])

        #({'username': 'maja_corethvonundzucoredoundstarkenberg',
        #      'email': 'maja_corethvonundzucoredoundstarkenberg@fakeiypt.nlogn.org', 'first_name': 'Maja',
        #      'last_name': 'Coreth von und zu Coredo und Starkenberg'},)

        usernames = []
        for t in trn.teams:
            for m in t.members:
                print("create user:",m.username)
                ctr = 0
                username = m.username
                while username in usernames:
                    ctr += 1
                    username = "%s-%d"%(m.username,ctr)

                    print("use alternative username")
                m.username = username
                usernames.append(username)
                root_mgnt.create_user(username=username, email="%s@fakeiypt.nlogn.org"%username, first_name=m.first_name, last_name=m.last_name)
            for tl in t.teamleaders:
                ctr = 0
                username = tl.username
                while username in usernames:
                    ctr += 1
                    username = "%s-%d" % (tl.username, ctr)
                tl.username = username
                usernames.append(username)
                root_mgnt.create_user(username=username, email="%s@fakeiypt.nlogn.org"%username, first_name=tl.first_name, last_name=tl.last_name)

        for j in trn.independent_jurors+trn.local_jurors:
            ctr = 0
            username = j.username
            while username in usernames:
                ctr += 1
                username = "%s-%d" % (j.username, ctr)
            j.username = username
            usernames.append(username)
            root_mgnt.create_user(username=username, email="%s@fakeiypt.nlogn.org" % username,
                                  first_name=j.first_name, last_name=j.last_name)


        root_mgnt.add_persons_to_tournament(["root", "admin"], ["test-iypt"])

        self.setup_permissions()

        admin_tournament = tournament.TournamentTests("admin")

        for p in trn.problems:
            admin_tournament.add_problem(*p)

        for t in AttendeeProperty.TYPE_CHOICES:
            admin_tournament.add_attendee_property("standalone data-"+t[1],"need it for test, should copy from profile",t[0])
            try:
                up = UserProperty.objects.get(type=t[0])
                admin_tournament.add_attendee_property("copy data-" + t[1], "need it for test", t[0], user_property=up.id)
            except UserProperty.DoesNotExist:
                pass

        admin_registration = registration.RegistrationTests("admin")
        for t in trn.teams:
            leader_registration = registration.RegistrationTests(t.teamleaders[0].username)
            leader_registration.apply_new_team("test-iypt", t.country)

            app = Application.objects.get(tournament__slug="test-iypt", applicant__user__username=t.teamleaders[0].username)
            admin_registration.accept_new_team(app)

            leader_account = account.AccountTests(t.teamleaders[0].username)

            leader_account.set_active_tournament("test-iypt")
            leader_registration.set_team_password(slugify(t.country), "blub")

            tm = TeamMember.objects.get(attendee__active_user__user__username=t.teamleaders[0].username)

            leader_registration.set_team_role(tm,TeamRole.LEADER,manager=True)

            leaderjuror_registration = registration.RegistrationTests(t.teamleaders[1].username)
            leaderjuror_registration.apply_possible_juror("test-iypt")

            leaderjuror_registration.apply_as_member("test-iypt", slugify(t.country), "blub",TeamRole.LEADER)

            for m in t.members:
                member_registration = registration.RegistrationTests(m.username)
                member_registration.apply_as_member("test-iypt", slugify(t.country), "blub")

        admin_jury = jury.JuryTests("admin")
        for t in trn.teams:
            leader_registration = registration.RegistrationTests(t.teamleaders[0].username)

            pJ = PossibleJuror.objects.get(person__user__username=t.teamleaders[1].username)
            admin_jury.accept_possible_juror(pJ)

            appl = Application.objects.get(team__origin__slug=slugify(t.country), applicant__user__username=t.teamleaders[1].username,
                                           tournament=leader_registration.user.profile.tournament)
            leader_registration.accept_team_member(appl)

            for m in t.members:
                try:
                    appl = Application.objects.get(team__origin__slug=slugify(t.country), applicant__user__username=m.username,
                                               tournament=leader_registration.user.profile.tournament)
                except:
                    appls = Application.objects.filter(team__origin__slug=slugify(t.country),
                                                   applicant__user__username=m.username,
                                                   tournament=leader_registration.user.profile.tournament)
                    print("duplicate applications")
                    print(appls)
                    print(appls[0])
                    print(appls[1])
                    self.assertEqual(len(appls),1)
                leader_registration.accept_team_member(appl)


        admin_plan = plan.PlanTests("admin")

        admin_plan.generate_placeholders()
                

    def test_individual(self):

        Log.step("Bootstrapping")

        root_mgnt = management.ManagementTests("root")

        root_mgnt.create_tournament("Test IYPT", "test-iypt")

        root_mgnt.create_user(username= "admin", email= "iypt-admin@x.xx", first_name= "The",
                              last_name= "Admin")
        root_mgnt.create_user(username="leader", email="iypt-tl@x.xx", first_name="The", last_name="Leader")
        root_mgnt.create_user(username="member", email="iypt-hans@x.xx", first_name="The", last_name="Hans")

        root_mgnt.set_password("admin","blablub")
        root_mgnt.set_password("leader","blablub")
        root_mgnt.set_password("member","blablub")

        Log.step("Prepare Tournament Admin")

        root_mgnt.add_persons_to_tournament(["root","admin"],["test-iypt"])

        self.setup_permissions()

        leader_registration = registration.RegistrationTests("leader")

        leader_registration.apply_new_team("test-iypt","MyCountry")

        Log.step("Admin accepts new team")

        admin_registration = registration.RegistrationTests("admin")

        app = Application.objects.get(tournament__slug="test-iypt",applicant__user__username="leader")
        admin_registration.accept_new_team(app)

        Log.step("Teamleader manages settings of team")

        leader_account = account.AccountTests("leader")

        leader_account.set_active_tournament("test-iypt")
        leader_registration.set_team_password("mycountry","blub")

        Log.step("Teammember applies for team")

        member_registration = registration.RegistrationTests("member")
        member_registration.apply_as_member("test-iypt","mycountry","blub")

        Log.step("Teamleader accepts member")

        appl = Application.objects.get(team__origin__slug="mycountry",applicant__user__username="member", tournament=leader_registration.user.profile.tournament)
        leader_registration.accept_team_member(appl)
