import os
import sys
import unittest

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import NoReverseMatch, resolve, reverse
from django.urls.resolvers import URLPattern, URLResolver

from apps.tournament.models import Tournament
from cc.settings import BASE_DIR

appsdir = os.path.join(BASE_DIR, "apps")
if appsdir in sys.path:
    sys.path.remove(appsdir)
if True:
    from cc.urls import urlpatterns


def _add_url(prefix, pattern_list):
    li = []
    for pattern in pattern_list:
        if type(pattern) == URLPattern:
            li.append("%s:%s" % (prefix, pattern.name))
        elif type(pattern) == URLResolver:
            if pattern.namespace and pattern.namespace != "djdt":
                ns = pattern.namespace
                if prefix:
                    print(prefix)
                    ns = "%s:%s" % (prefix, ns)
                li += _add_url(ns, pattern.url_patterns)
    return li


class GetTest(TestCase):

    fixtures = ["data/tests/2016andMore.json"]

    exclude_urls = [
        "jury:assign_new",
        "fight:genpdfpreview",
        "fight:genpdfresult",
        "fight:genpdfrank",
        "account:invoice_account",
        "account:avatar",
    ]

    def setUp(self):
        user = User.objects.get(username="root")
        # user = self.create_team_leader()
        self.client.force_login(user)

    url_names = _add_url(None, urlpatterns)

    vs = vars()

    def make_test_function(idx, url_name, url):
        def t(self):
            response = self.client.get(url)
            self.assertTrue(response.status_code in [200, 302, 405])

        t.__name__ = "test_" + idx
        t.__doc__ = "simple get test for " + url_name
        return t

    def make_skip_function(idx, url_name):
        def t(self):
            pass

        t.__name__ = "test_" + idx
        t.__doc__ = (
            "skip test for " + url_name + " requires parameter(s) or view not found"
        )
        return t

    for i, url_name in enumerate(url_names):
        if url_name in exclude_urls:
            continue
        i = str(i)
        try:
            url = reverse(url_name, args=(), kwargs={})
            vs["test_" + i] = make_test_function(i, url_name, url)
        except NoReverseMatch as e:
            vs["test_" + i] = make_skip_function(i, url_name)
            # unittest.skip(url_name + ' requires parameter(s) or view not found')

    del (
        url_names,
        vs,
        make_test_function,
    )


class MonkeyTest(TestCase):

    fixtures = ["data/tests/2016andMore.json"]

    def setUp(self):
        user = User.objects.get(username="root")
        self.client.force_login(user)
        for t in Tournament.objects.all():
            t.results_access = Tournament.RESULTS_PUBLIC
            t.save()

    def test_recursive(self):

        import re

        url_names = _add_url(None, urlpatterns[1:])

        checked = set()
        to_check = set()

        for url_name in url_names:
            try:
                url = reverse(url_name, args=(), kwargs={})
                checked.add(url)
                if url == "/dashboard/logout":
                    continue
                result = self.client.get(url)
                if result.status_code == 200:
                    urls = re.findall(r'href=[\'"]?([^\'"]+)', result.content.decode())
                    for url in urls:
                        try:
                            res = resolve(url)
                            if len(res.kwargs) > 0:
                                to_check.add(url)
                        except:
                            pass
            except:
                pass

        timeout = 10000
        while len(to_check) > 0:
            timeout -= 1

            self.assertTrue(timeout > 0, msg="Site timeout")

            url = list(to_check)[0]
            to_check.discard(url)
            checked.add(url)

            print("start with %s" % url)
            if url == "/dashboard/logout":
                print("skipped logout")
                continue
            if url.startswith("/fight/fight/") and url.endswith("/genpreview/"):
                print("skipped preview generation")
                continue
            if url.startswith("/fight/fight/") and url.endswith("/genresult/"):
                print("skipped result generation")
                continue
            if url.startswith("/fight/") and url.endswith("/genrank/"):
                print("skipped rank generation")
                continue
            if url.startswith("/account/accounts/") and url.endswith("/invoice/"):
                print("skipped invoice generation")
                continue

            result = self.client.get(url, follow=True)
            if len(result.redirect_chain) > 0:
                print("redir to %s" % result.redirect_chain)
            self.assertTrue(result.status_code in [200, 302, 405], msg="View Failed")

            if result.status_code == 200:
                urls = re.findall(r'href=[\'"]?([^\'"]+)', result.content.decode())
                for suburl in urls:
                    try:
                        res = resolve(suburl)
                        if len(res.kwargs) > 0 and suburl not in checked:
                            to_check.add(suburl)
                    except:
                        pass
