import yaml
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from formtools.preview import FormPreview

from apps.plan.models import Room
from apps.team.models import Team
from apps.tournament.models import Origin


@method_decorator(login_required, name="__call__")
class ImportPreview(FormPreview):

    form_template = "fake/import.html"
    preview_template = "fake/import_preview.html"

    def process_preview(self, request, form, context):
        d = form.cleaned_data["input"]

        data = yaml.safe_load(d)
        context["data"] = data

    def done(self, request, cleaned_data):
        d = cleaned_data["input"]
        data = yaml.safe_load(d)

        trn = request.user.profile.tournament

        for room in data["rooms"].keys():
            r = data["rooms"][room]
            newroom = Room.objects.get_or_create(tournament=trn, name=r["name"])[0]
            r["obj"] = newroom
        print(data["rooms"])

        for team_id in data["teams"].keys():
            t = data["teams"][team_id]
            newo = Origin.objects.get_or_create(
                tournament=trn, name=t["origin"]["name"]
            )[0]
            newteam = Team.objects.get_or_create(tournament=trn, origin=newo)[0]
            t["obj"] = newteam

        print(data["teams"])
        return redirect("fake:import")
