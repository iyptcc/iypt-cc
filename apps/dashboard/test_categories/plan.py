from .verbose_testcase import VerboseTestCase


class PlanTests(VerboseTestCase):

    def generate_placeholders(self):
        r = self.client.post("/plan/placeholder/teams/generate")
        self.assertIn(r.status_code, [302, 200])
