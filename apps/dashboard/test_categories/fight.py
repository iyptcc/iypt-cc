import random

from apps.account.models import Attendee
from apps.plan.models import Fight, Round, Stage
from apps.tournament.models import Problem, Tournament

from .verbose_testcase import VerboseTestCase


class FightTests(VerboseTestCase):
    pass

    def assign_fa(self, trns, assistants):
        trn = Tournament.objects.get(slug=trns)

        attids = Attendee.objects.filter(
            active_user__user__username__in=[fa.username for fa in assistants]
        ).values_list("pk", flat=True)

        attr = {}
        for round in trn.round_set(manager="selectives").all():
            for fight in round.fight_set.select_related("room").all():
                attr["op-%d-%d" % (round.order, fight.pk)] = attids

        r = self.client.post("/fight/manage/", attr)
        self.assertIn(r.status_code, [200, 302])

    def fill_stage(self, stage: Stage):

        trn = stage.fight.round.tournament

        data = {}

        data["presented"] = random.choice(
            trn.problem_set.all().values_list("pk", flat=True)
        )

        print("in stage", stage)
        data["rep"] = random.choice(
            stage.rep_attendance.team.teammember_set(manager="students")
            .all()
            .values_list("pk", flat=True)
        )
        data["opp"] = random.choice(
            stage.opp_attendance.team.teammember_set(manager="students")
            .all()
            .values_list("pk", flat=True)
        )
        data["rev"] = random.choice(
            stage.rev_attendance.team.teammember_set(manager="students")
            .all()
            .values_list("pk", flat=True)
        )

        for js in stage.fight.jurorsession_set(manager="voting").all():
            data["grade-%d-rep" % (js.pk,)] = random.choice(range(1, 11))
            data["grade-%d-opp" % (js.pk,)] = random.choice(range(1, 11))
            data["grade-%d-rev" % (js.pk,)] = random.choice(range(1, 11))

        print(data)
        r = self.client.post(
            "/fight/fight/%d/%d/" % (stage.fight.id, stage.order), data
        )
        self.assertIn(r.status_code, [200, 302])

    def lock_fight(self, fight: Fight):
        r = self.client.post(
            "/fight/fight/%d/check/" % (fight.id,), {"_save": "save and lock"}
        )
        self.assertIn(r.status_code, [200, 302])

    def fake_all(self, trns):

        for fight in Fight.objects.filter(round__tournament__slug=trns):
            for s in fight.stage_set.all():
                self.fill_stage(s)
            self.lock_fight(fight)

    def fake_final(self, trns):
        fi = Round.finals.get(tournament__slug=trns).fight_set.first()
        for s in fi.stage_set.all():
            self.fill_stage(s)
        self.lock_fight(fi)

    def validate_all(self, trns):
        for fight in Fight.objects.filter(round__tournament__slug=trns):
            r = self.client.post(
                "/fight/fight/%d/check/" % (fight.id,), {"_validate": "validate"}
            )
            self.assertIn(r.status_code, [200, 302])

    def publish_all(self, trns):
        data = {"protection": "pub"}
        for ro in Round.selectives.filter(tournament__slug=trns):
            data["rank-%d" % ro.order] = "on"
            data["sched-%d" % ro.order] = "on"

            for fight in ro.fight_set.all():
                data["grades-%d-%d" % (ro.order, fight.pk)] = "on"
                if ro.order > 1:
                    data["preview-%d-%d" % (ro.order, fight.pk)] = "on"
        print(data)
        r = self.client.post("/fight/publish/", data)
        self.assertIn(r.status_code, [200, 302])
