from oauth2_provider.views.base import AuthorizationView

from apps.tournament.models import Tournament


class MyAuthorizationView(AuthorizationView):
    def dispatch(self, request, *args, **kwargs):

        try:
            if not Tournament.objects.filter(
                activeuser=request.user.profile, allow_oauth=True
            ).exists():
                return self.handle_no_permission()
        except Exception:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
