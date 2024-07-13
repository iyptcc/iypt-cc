import inspect
from unittest import TestCase

from django.contrib.auth.models import User
from django.test import Client

from .utils import Log


class VerboseClient(Client):

    def post(self, path, *args, **kwargs):
        print("try a get to same url")
        r = super().get(path)
        try:
            redirect = r._headers["location"][1]
            if redirect.startswith("/auth/login/?next=/"):
                r.status_code = 403
        except:
            pass
        print("returned code: ", r.status_code)
        if r.status_code not in [200, 302, 405]:
            raise Exception("get not successful")

        return self.post_only(path, *args, **kwargs)

    def post_only(self, path, *args, **kwargs):
        print("only post to %s with arguments:" % path)
        print(args)
        r = super().post(path, *args, **kwargs)
        try:
            redirect = r._headers["location"][1]
            if redirect.startswith("/auth/login/?next=/"):
                r.status_code = 403
        except:
            pass
        return r


class VerboseTestCase(TestCase):

    def __getattribute__(self, name):
        try:
            attr = object.__getattribute__(self, name)
        except:
            attr = super().__getattribute__(name)

        if hasattr(attr, "__call__") and inspect.ismethod(attr):

            def newfunc(*args, **kwargs):
                if not (
                    attr.__name__.startswith("_")
                    or attr.__name__.startswith("assert")
                    or attr.__name__.startswith("addTypeEqualityFunc")
                ):
                    arg = ", ".join([str(a) for a in args])
                    Log.info("Calling %s(%s)" % (attr.__name__, arg))
                result = attr(*args, **kwargs)
                return result

            return newfunc
        else:
            return attr

    def __init__(self, username, **kwargs):
        super().__init__(**kwargs)

        print("username:%s" % username)
        self.client = VerboseClient()
        try:
            self.user = User.objects.get(username=username)
            self.client.force_login(self.user)
        except:
            self.user = None

    def _preview_post(self, url, args, ndargs=None, debug=False):
        r = self.client.post(url, args)

        if debug:
            print(r.content)
            print(r.context)
            print(r.context["hash_value"])

        if ndargs:
            args.update(ndargs)
        args.update({"stage": 2, "hash": r.context["hash_value"]})

        r = self.client.post(url, args)

        self.assertIn(r.status_code, [200, 302])

    def _wizard_post(self, url, args, ndargs=None, debug=False):
        args["apply_with_role_wizard-current_step"] = "role"
        r = self.client.post(url, args)

        if debug:
            print(r.content)
            print(r.context)

        if ndargs:
            args.update(ndargs)
        args = {}
        args["apply_with_role_wizard-current_step"] = "questions"

        r = self.client.post_only(url, args)

        self.assertIn(r.status_code, [200, 302])
