from django.contrib.auth.models import User

from apps.account.models import ActiveUser
from apps.registration.models import UserProperty
from apps.tournament.models import Tournament

from .verbose_testcase import VerboseTestCase


class ManagementTests(VerboseTestCase):

    def __init__(self,username,**kwargs):
        self.create_root(username="root", password="blubblub")
        super().__init__(username, **kwargs)

    def create_root(self,**kwargs):
        root = User.objects.get_or_create(username="root", email="fe-x@nlogn.org", is_staff=True, is_superuser=True,
                                   password="pbkdf2_sha256$30000$bfSRcz8435Km$VOJasXkSscLPajzWpi3An2aA8YKkn9keyX/FGassy/k=")[0]
        au = ActiveUser.objects.get_or_create(user=root)


    def create_tournament(self,name,slug):
        r = self.client.post("/management/create/", {"name": name, "slug": slug})

        self.assertIn(r.status_code, [200, 302])

    def create_user(self,*args,**kwargs):
        r = self.client.post("/management/users/create",
                             kwargs)
        print(r)
        print(User.objects.all())
        User.objects.get(username=kwargs["username"])
        self.assertIn(r.status_code, [200, 302])

    def set_password(self,username, password):
        u = User.objects.get(username=username)
        r = self.client.post("/management/users/%d/password" % u.id, {"password": password})
        self.assertIn(r.status_code, [200, 302])

    def add_persons_to_tournament(self,usernames,tournaments):
        trns = Tournament.objects.filter(slug__in=tournaments).values_list("id",flat=True)
        print(trns)
        userids = User.objects.filter(username__in=usernames).values_list("id",flat=True)
        print(userids)
        self._preview_post("/management/users/",{"tournaments": trns, "_add_tournaments": "add tournaments for selected","persons": userids},{"action": "_add_tournaments"})

    def add_profile_property(self,name,type):
        r = self.client.post("/management/profile/create/", {"name":name,"type":type})
        self.assertIn(r.status_code, [200, 302])
        UserProperty.objects.get(name=name,type=type)
