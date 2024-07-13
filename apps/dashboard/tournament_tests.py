import datetime
import os
from glob import glob

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils import timezone

from apps.account.models import ParticipationRole
from apps.jury.models import PossibleJuror
from apps.registration.models import Application, AttendeeProperty, UserProperty
from apps.schedule.utils import import_template
from apps.team.models import Team, TeamMember, TeamRole

from .test_categories import (
    account,
    fakedata,
    fight,
    jury,
    management,
    plan,
    registration,
    tournament,
)
from .test_categories.utils import Log
from .test_categories.verbose_testcase import VerboseTestCase


class FullTournament(VerboseTestCase):
    databases = ["default"]

    def runTest(self):
        self.setup_plans()
        self.test_full()
        # self.test_individual()

    def setup_plans(self):
        for f in glob(os.path.join(settings.BASE_DIR, "data", "templates", "*")):
            import_template(f)

    def setup_permissions(self):
        root_account = account.AccountTests("root")

        root_account.set_active_tournament("test-iypt")

        root_tournament = tournament.TournamentTests(username="root")

        root_tournament.create_perm_group(
            "admin-group",
            [
                "tournament.app_tournament",
                "tournament.app_plan",
                "plan.view_plan",
                "auth.add_group",
                "auth.change_group",
                "account.view_all_persons",
                "tournament.change_tournament",
                "registration.manage_data",
                "registration.manage_team",
                "registration.accept_team",
                "account.add_participationrole",
                "account.change_participationrole",
                "account.delete_participationrole",
                "tournament.add_problem",
                "tournament.change_attendee_data",
                "tournament.app_jury",
                "jury.change_juror",
                "registration.accept_role",
                "registration.accept_juror",
                "plan.add_teamplaceholder",
                "plan.add_round",
                "plan.view_placeholders",
                "plan.assign_placeholders",
                "plan.apply_schedule",
                "account.view_all_persons",
                "account.change_attendee",
                "jury.change_jurorsession",
                "plan.view_fight_operator",
                "tournament.app_fight",
                "plan.change_fight_operator",
                "jury.validate_grades",
                "jury.change_all_jurorsessions",
                "jury.publish_fights",
                "plan.change_final",
            ],
        )

        root_tournament.add_groups_to_persons(["admin-group"], ["admin"])

        Log.step("Tournament Admin preparation")

        admin_account = account.AccountTests("admin")

        admin_account.set_active_tournament("test-iypt")

        admin_tournament = tournament.TournamentTests("admin")
        admin_tournament.tournament_settings(
            timezone.now() - datetime.timedelta(days=2),
            timezone.now() + datetime.timedelta(days=2),
        )

        Log.step("Create Permission Groups")

        admin_tournament.create_perm_group("tl-group", ["registration.manage_team"])
        admin_tournament.create_perm_group(
            "participant-group", ["registration.manage_data"]
        )
        admin_tournament.create_perm_group(
            "fa-group", ["jury.change_jurorsession", "tournament.app_fight"]
        )

        admin_tournament.add_groups_to_role(["tl-group", "participant-group"], "tl")
        admin_tournament.add_groups_to_role(["participant-group"], "st")
        admin_tournament.add_groups_to_role(["fa-group"], "fa")

    def test_full(self):

        trn = fakedata.FakeTournament("en_GB", 7, 5, 10, 15, f_ass=5)

        Log.step("Bootstrapping")

        root_mgnt = management.ManagementTests("root")

        root_mgnt.create_tournament("Test IYPT", "test-iypt")

        root_mgnt.create_user(
            username="admin",
            email="iypt-admin@x.xx",
            first_name="The",
            last_name="Admin",
        )

        Log.step("Create User Properties")

        for t in UserProperty.TYPE_CHOICES:
            root_mgnt.add_profile_property("profile data-" + t[1], t[0])

        usernames = []
        for t in trn.teams:
            for m in t.members:
                print("create user:", m.username)
                ctr = 0
                username = m.username
                while username in usernames:
                    ctr += 1
                    username = "%s-%d" % (m.username, ctr)

                    print("use alternative username")
                m.username = username
                usernames.append(username)
                root_mgnt.create_user(
                    username=username,
                    email="%s@fakeiypt.nlogn.org" % username,
                    first_name=m.first_name,
                    last_name=m.last_name,
                )
            for tl in t.teamleaders:
                ctr = 0
                username = tl.username
                while username in usernames:
                    ctr += 1
                    username = "%s-%d" % (tl.username, ctr)
                tl.username = username
                usernames.append(username)
                root_mgnt.create_user(
                    username=username,
                    email="%s@fakeiypt.nlogn.org" % username,
                    first_name=tl.first_name,
                    last_name=tl.last_name,
                )

        for j in trn.independent_jurors + trn.local_jurors + trn.fight_assistants:
            ctr = 0
            username = j.username
            while username in usernames:
                ctr += 1
                username = "%s-%d" % (j.username, ctr)
            j.username = username
            usernames.append(username)
            root_mgnt.create_user(
                username=username,
                email="%s@fakeiypt.nlogn.org" % username,
                first_name=j.first_name,
                last_name=j.last_name,
            )

        root_mgnt.add_persons_to_tournament(["root", "admin"], ["test-iypt"])

        self.setup_permissions()

        admin_tournament = tournament.TournamentTests("admin")

        Log.step("Create Problems")

        for p in trn.problems:
            admin_tournament.add_problem(*p)

        Log.step("Create Attendee Properties")

        for t in AttendeeProperty.TYPE_CHOICES:
            admin_tournament.add_attendee_property(
                "standalone data-" + t[1],
                "need it for test, should copy from profile",
                t[0],
            )
            try:
                up = UserProperty.objects.get(type=t[0])
                admin_tournament.add_attendee_property(
                    "copy data-" + t[1], "need it for test", t[0], user_property=up.id
                )
            except UserProperty.DoesNotExist:
                pass

        admin_registration = registration.RegistrationTests("admin")
        for t in trn.teams:
            leader_registration = registration.RegistrationTests(
                t.teamleaders[0].username
            )
            leader_registration.apply_new_team("test-iypt", t.country)

            app = Application.objects.get(
                tournament__slug="test-iypt",
                applicant__user__username=t.teamleaders[0].username,
            )
            admin_registration.accept_new_team(app)

            leader_account = account.AccountTests(t.teamleaders[0].username)

            leader_account.set_active_tournament("test-iypt")
            leader_registration.set_team_password(slugify(t.country), "blub")

            tm = TeamMember.objects.get(
                attendee__active_user__user__username=t.teamleaders[0].username
            )

            leader_registration.set_team_role(tm, TeamRole.LEADER, manager=True)

            leaderjuror_registration = registration.RegistrationTests(
                t.teamleaders[1].username
            )
            leaderjuror_registration.apply_possible_juror("test-iypt")

            leaderjuror_registration.apply_as_member(
                "test-iypt", slugify(t.country), "blub", TeamRole.LEADER
            )

            for m in t.members:
                member_registration = registration.RegistrationTests(m.username)
                member_registration.apply_as_member(
                    "test-iypt", slugify(t.country), "blub"
                )

        admin_jury = jury.JuryTests("admin")
        for t in trn.teams:
            leader_registration = registration.RegistrationTests(
                t.teamleaders[0].username
            )

            pJ = PossibleJuror.objects.get(
                person__user__username=t.teamleaders[1].username
            )
            admin_jury.accept_possible_juror(pJ)

            appl = Application.objects.get(
                team__origin__slug=slugify(t.country),
                applicant__user__username=t.teamleaders[1].username,
                tournament=leader_registration.user.profile.tournament,
            )
            leader_registration.accept_team_member(appl)

            for m in t.members:
                try:
                    appl = Application.objects.get(
                        team__origin__slug=slugify(t.country),
                        applicant__user__username=m.username,
                        tournament=leader_registration.user.profile.tournament,
                    )
                except:
                    appls = Application.objects.filter(
                        team__origin__slug=slugify(t.country),
                        applicant__user__username=m.username,
                        tournament=leader_registration.user.profile.tournament,
                    )
                    print("duplicate applications")
                    print(appls)
                    print(appls[0])
                    print(appls[1])
                    self.assertEqual(len(appls), 1)
                leader_registration.accept_team_member(appl)

        for ij in trn.independent_jurors:
            juror_registration = registration.RegistrationTests(ij.username)
            juror_registration.apply_possible_juror("test-iypt")

            pJ = PossibleJuror.objects.get(person__user__username=ij.username)
            admin_jury.accept_possible_juror(pJ)

        juror_role = ParticipationRole.objects.get(
            tournament=admin_jury.user.profile.tournament, type=ParticipationRole.JUROR
        )
        for ij in trn.independent_jurors:
            juror_registration = registration.RegistrationTests(ij.username)
            juror_registration.apply_role("test-iypt", juror_role)

            app = Application.objects.get(
                tournament__slug="test-iypt", applicant__user__username=ij.username
            )
            admin_registration.accept_role(app)

        fa_role = ParticipationRole.objects.get(
            tournament=admin_jury.user.profile.tournament,
            type=ParticipationRole.FIGHT_ASSISTANT,
        )
        for fa in trn.fight_assistants:
            fa_registration = registration.RegistrationTests(fa.username)
            fa_registration.apply_role("test-iypt", fa_role)

            app = Application.objects.get(
                tournament__slug="test-iypt", applicant__user__username=fa.username
            )
            admin_registration.accept_role(app)

            fa_account = account.AccountTests(fa.username)
            fa_account.set_active_tournament("test-iypt")

        admin_plan = plan.PlanTests("admin")

        admin_plan.generate_placeholders()

        admin_plan.load_schedule(
            Team.objects.filter(tournament=admin_plan.user.profile.tournament).count()
        )

        admin_plan.assign_random_placeholders()

        admin_plan.apply_teams()

        Log.step("Create Jurors from Teamleaders")

        admin_plan.get_attendees()

        admin_plan.create_jurors()

        admin_jury.set_chairs()

        admin_jury.set_all_available()

        res = admin_jury.start_assign()
        admin_jury.apply_jurors(res)

        Log.step("Assign FA to fights")

        admin_fight = fight.FightTests("admin")

        admin_fight.assign_fa("test-iypt", trn.fight_assistants)

        fa_fight = fight.FightTests(trn.fight_assistants[0].username)

        fa_fight.fake_all("test-iypt")

        admin_fight.validate_all("test-iypt")

        admin_fight.publish_all("test-iypt")

        admin_plan.create_final("test-iypt")

        admin_jury.final_jury("test-iypt")

        admin_fight.fake_final("test-iypt")

        admin_fight.validate_all("test-iypt")
