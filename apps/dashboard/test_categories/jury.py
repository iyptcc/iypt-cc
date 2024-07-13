from celery.result import AsyncResult
from django.utils import timezone

from apps.jury.anealing import assignAneal
from apps.jury.models import AssignResult, Juror, JurorRole, JurorSession
from apps.plan.models import Fight, Round

from .verbose_testcase import VerboseTestCase


class JuryTests(VerboseTestCase):

    def accept_possible_juror(self, pJ):

        r = self.client.post(
            "/jury/possible/accept/%d/" % (pJ.id), {"experience": pJ.experience}
        )
        self.assertIn(r.status_code, [302, 200])

    def start_assign(self):

        # res = assignJob(self.user.profile.tournament.id, total_rounds=1000, room_jurors=5, cooling_base=0.99,
        #                      fix_rounds=0)
        # print(res)
        # AssignResult.objects.create(tournament=self.user.profile.tournament, task_id=res.id, author=self.user.profile.active,
        #                            total_rounds=1000, room_jurors=5, cooling_base=0.99,
        #                            fix_rounds=0)

        task_id = "550e8400-e29b-11d4-a716-446655440000"
        AssignResult.objects.create(
            tournament=self.user.profile.tournament,
            task_id=task_id,
            author=self.user.profile.active,
            total_rounds=1000,
            room_jurors=5,
            cooling_base=0.99,
            fix_rounds=0,
        )

        best_plan, best_cost = assignAneal(
            self.user.profile.tournament.id,
            total_rounds=1000,
            room_jurors=5,
            cooling_base=0.99,
            fix_rounds=0,
        )

        if len(best_plan) == 0:
            return ([], best_cost)

        plan = []

        for round in best_plan:

            round_fights = []

            for fight in round["fights"]:

                fight_data = {
                    "pk": fight["fight"].pk,
                    "room": fight["fight"].room.name,
                    "jurors": [],
                    "nonvoting": [],
                }

                chair = list(filter(lambda j: j.possible_chair, fight["jurors"]))[0]

                fight_data["chair"] = {"id": chair.pk, "name": chair.attendee.full_name}

                for juror in fight["jurors"]:
                    if juror != chair:
                        fight_data["jurors"].append(
                            {"id": juror.pk, "name": juror.attendee.full_name}
                        )

                for juror in fight["nonvoting"]:
                    fight_data["nonvoting"].append(
                        {"id": juror.pk, "name": juror.attendee.full_name}
                    )

                round_fights.append(fight_data)

            plan.append(round_fights)

        ar = AssignResult.objects.get(task_id=task_id)
        ar.finished = timezone.now()
        ar.save()

        return (plan, best_cost)

    def apply_jurors(self, result):

        trn = self.user.profile.tournament

        if not JurorSession.objects.filter(
            fight__round__tournament=trn, fight__round__order__gt=0
        ).exists():
            if len(result[0]) > 0:
                chair_role = JurorRole.objects.get(type=JurorRole.CHAIR, tournament=trn)
                juror_role = JurorRole.objects.get(type=JurorRole.JUROR, tournament=trn)
                nonvote_role = JurorRole.objects.get(
                    type=JurorRole.NONVOTING, tournament=trn
                )

                plan = result[0]
                for round in plan:
                    for fight in round:
                        fobj = Fight.objects.get(pk=fight["pk"])
                        chair = Juror.objects.get(pk=fight["chair"]["id"])
                        jurors = Juror.objects.filter(
                            id__in=list(map(lambda x: x["id"], fight["jurors"]))
                        )
                        nonvoting = Juror.objects.filter(
                            id__in=list(map(lambda x: x["id"], fight["nonvoting"]))
                        )

                        JurorSession.objects.create(
                            juror=chair, fight=fobj, role=chair_role
                        )
                        for juror in jurors:
                            JurorSession.objects.create(
                                juror=juror, fight=fobj, role=juror_role
                            )
                        for juror in nonvoting:
                            JurorSession.objects.create(
                                juror=juror, fight=fobj, role=nonvote_role
                            )

    def set_chairs(self):
        j = (
            Juror.objects.filter(attendee__tournament=self.user.profile.tournament)
            .order_by("-id")[:7]
            .values_list("id", flat=True)
        )
        self._preview_post(
            "/jury/list",
            {
                "possible_chair_set": True,
                "possible_chair": True,
                "_set_parameters": "set parameters",
                "jurors": j,
            },
            {"action": "_set_parameters"},
        )

        chairs = Juror.objects.filter(
            attendee__tournament=self.user.profile.tournament, possible_chair=True
        )
        print("chairs:")
        print(chairs)

    def set_all_available(self):
        j = Juror.objects.filter(
            attendee__tournament=self.user.profile.tournament
        ).values_list("id", flat=True)
        avail = {}
        for r in self.user.profile.tournament.round_set.all():
            avail["round_%d_set" % r.order] = True
            avail["round_%d" % r.order] = True
        self._preview_post(
            "/jury/list",
            {**avail, "_set_parameters": "set parameters", "jurors": j},
            {"action": "_set_parameters"},
        )

    def final_jury(self, trns):
        fi = Round.finals.get(tournament__slug=trns).fight_set.first()
        jurors = Juror.objects.filter(attendee__tournament__slug=trns)

        data = {"chair": jurors[0].pk}
        data["jurors"] = jurors[2:7].values_list("pk", flat=True)
        self.client.post("/jury/fight/%d" % fi.pk, data)
