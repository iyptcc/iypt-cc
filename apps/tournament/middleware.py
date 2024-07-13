from django.contrib.auth.decorators import permission_required

from apps.tournament.models import Tournament


class AppPermissionMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # An exception match should immediately return None

        # for path in self.exceptions:
        #    if path.match(request.path): return None
        #    # Requests matching a restricted URL pattern are returned
        # wrapped with the permission_required decorator

        # for rule in self.restricted:
        #    url, required_permission = rule[0], rule[1]
        #    if url.match(request.path):
        #        return permission_required(required_permission)(view_func)(request, *view_args, **view_kwargs)
        #        # Explicitly return None for all non-matching requests

        perms = []
        avail_perms = list(map(lambda x: x[0], Tournament._meta.permissions))
        for app in request.resolver_match.app_names:
            if "app_%s" % app in avail_perms:
                perms.append("tournament.app_%s" % app)

        return permission_required(perms)(view_func)(request, *view_args, **view_kwargs)
