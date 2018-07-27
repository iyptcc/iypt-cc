from .verbose_testcase import VerboseTestCase


class JuryTests(VerboseTestCase):

    def accept_possible_juror(self,pJ):

        r = self.client.post("/jury/possible/accept/%d/" % (pJ.id), {"experience":pJ.experience})
        self.assertIn(r.status_code, [302, 200])
