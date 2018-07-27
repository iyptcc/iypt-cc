from django.contrib.auth.models import Group, Permission

from apps.account.models import Attendee, ParticipationRole
from apps.registration.models import AttendeeProperty

from .verbose_testcase import VerboseTestCase


class TournamentTests(VerboseTestCase):

    def create_perm_group(self,name, perms):
        ids = []
        for p in perms:
            pp = p.split(".")
            ids.append(Permission.objects.get(content_type__app_label=pp[0], codename=".".join(pp[1:])).id)
        r = self.client.post("/tournament/rights/groups/create/", {"name":name, "permissions": ids})
        self.assertIn(r.status_code, [200,302])
        Group.objects.get(name=name)

    def add_groups_to_persons(self,groups,persons):

        print(Group.objects.all())
        g=Group.objects.filter(name__in=groups).values_list("id",flat=True)
        a=Attendee.objects.filter(active_user__user__username__in=persons).values_list("id",flat=True)
        print("add g to a:")
        print(g)
        print(a)
        self._preview_post("/plan/persons",
                           {"groups": g, "_add_groups": "add groups for selected",
                            "persons": a}, {"action": "_add_groups"}, False)

    def tournament_settings(self, start, end, rejections=3):
        r = self.client.post("/tournament/settings/", {"allowed_rejections": rejections})
        r = self.client.post("/tournament/settings/registration", {"registration_open": start.strftime("%Y-%m-%dT%H:%M%z"), "registration_close":end.strftime("%Y-%m-%dT%H:%M%z"),
                                                                   "registration_teamleaderjurors_required": 1,
                                                                   "registration_teamleaderjurors_required_guest": 0,
                                                                   "registration_apply_newteam": "on",
                                                                   "registration_apply_team":"on",})
        self.assertIn(r.status_code, [302,200])
        self.assertEqual(self.user.profile.tournament.registration_open.strftime("%Y-%m-%dT%H:%M%z"), start.strftime("%Y-%m-%dT%H:%M%z"))
        self.assertEqual(self.user.profile.tournament.registration_close.strftime("%Y-%m-%dT%H:%M%z"), end.strftime("%Y-%m-%dT%H:%M%z"))

    def add_groups_to_role(self,groups, role, attending=True):
        role = ParticipationRole.objects.get(tournament=self.user.profile.tournament, type=role)
        groups = Group.objects.filter(name__in=groups).values_list("id", flat=True)
        args = {"name": role.name,
                              "type": role.type,
                              "groups":groups }
        if attending:
            args.update({"attending":"on"})

        r = self.client.post("/tournament/rights/roles/edit/%d/" % role.id, args)
        self.assertIn(r.status_code, [302, 200])
        setgroups = ParticipationRole.objects.get(id=role.id).groups.values_list("id",flat=True)
        self.assertListEqual(list(sorted(groups)),list(sorted(setgroups)))

    def add_problem(self,number,title,description):
        r = self.client.post("/tournament/problems/create/",
                             {"description":description,
                                "number": number,
                                "title":title })
        print(r)
        self.assertIn(r.status_code, [302, 200])
        self.assertEqual(self.user.profile.tournament.problem_set.get(number=number).title, title)
        self.assertEqual(self.user.profile.tournament.problem_set.get(number=number).description, description)

    def add_attendee_property(self,name, desc, type, required = None, optional=None, user_property=None):

        if optional == None:
            optional = list(self.user.profile.tournament.participationrole_set.all().values_list("id",flat=True))

        if required == None:
            required = []

        if user_property == None:
            user_property = ""

        r = self.client.post("/tournament/participation_data/create/",
                             {"data_utilisation": desc,
                              "name": name,
                              "optional": optional,
                              "required": required,
                              "type": type,
                              "user_property":user_property})

        self.assertIn(r.status_code, [302, 200])

        print(r.content)

        AttendeeProperty.objects.get(tournament=self.user.profile.tournament, name=name,type=type)
