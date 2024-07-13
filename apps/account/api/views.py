from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from ..views import mmusername


class UserViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        # serializer = self.serializer_class(self.request.user.profile, many=False)
        a = {
            "id": request.user.id,
            "name": "%s %s" % (request.user.first_name, request.user.last_name),
            "displayName": "%s %s" % (request.user.first_name, request.user.last_name),
            "username": mmusername(request.user.username),
            "email": request.user.email,
            # "state": "active",
            # "avatar_url": "https://git.iypt.org/uploads/-/system/user/avatar/2/avatar.png",
            # "web_url": "https://git.iypt.org/felix.engelmann",
            # "created_at": "2019-10-26T21:35:54.222Z", "bio": "",
            # "location": "",
            # "public_email": "", "skype": "", "linkedin": "", "twitter": "", "website_url": "",
            # "organization": "", "last_sign_in_at": "2019-12-13T22:20:26.465Z",
            # "confirmed_at": "2019-10-26T21:35:53.321Z", "last_activity_on": "2020-01-22",
            # "email": "fe-iypt-git@nlogn.org", "theme_id": 1, "color_scheme_id": 1, "projects_limit": 100000,
            # "current_sign_in_at": "2019-12-26T15:52:15.623Z", "identities": [], "can_create_group": True,
            # "can_create_project": True, "two_factor_enabled": False, "external": False, "private_profile": False,
            # "is_admin": True
        }
        return Response(a)
