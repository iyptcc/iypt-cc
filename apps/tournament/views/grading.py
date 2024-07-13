import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from formtools.preview import FormPreview

from apps.dashboard.delete import ConfirmedDeleteView
from apps.jury.models import GradingCategory, GradingElement, GradingGroup


class GradingView(View):
    def get(self, request):
        elem = {}
        for fr in request.user.profile.tournament.fightrole_set.all():
            elems = []
            for gg in fr.gradinggroup_set.all():
                elems.append(
                    {"name": gg.name, "minimum": gg.minimum, "maximum": gg.maximum}
                )
            elem[fr.type] = elems

        return JsonResponse(elem)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("jury.add_gradinggroup", raise_exception=False), name="dispatch"
)
class GradingDelete(ConfirmedDeleteView):

    redirection = "tournament:grading"

    def get_objects(self, request, *args, **kwargs):
        try:
            return GradingGroup.objects.filter(
                role__tournament=request.user.profile.tournament
            ).all()
        except GradingGroup.DoesNotExist:
            return GradingGroup.objects.none()


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("jury.add_gradinggroup"), name="__call__")
class GradingImportPreview(FormPreview):

    form_template = "tournament/grading_import.html"
    preview_template = "tournament/grading_preview.html"

    def process_preview(self, request, form, context):

        data = form.cleaned_data["input"]
        try:
            plan = json.loads(data)
        except:
            plan = "error"
        context["grading"] = plan

    def done(self, request, cleaned_data):
        trn = request.user.profile.tournament
        if GradingGroup.objects.filter(role__tournament=trn).exists():
            messages.add_message(request, messages.ERROR, "grading sheet not empty")
            return redirect("tournament:grading")

        data = cleaned_data["input"]
        plan = json.loads(data)
        for role in plan.items():
            fr = trn.fightrole_set.get(type=role[0])
            print(fr)
            for grp in role[1]:
                grpo = GradingGroup.objects.create(
                    role=fr,
                    name=grp["name"],
                    minimum=grp["minimum"],
                    maximum=grp["maximum"],
                )
                for cat in grp.get("categories", []):
                    cattitle, elems = list(cat.items())[0]
                    # elems = list(cat.values())[0]
                    cato = GradingCategory.objects.create(title=cattitle, group=grpo)
                    for el in elems:
                        if set(el.keys()) == {"name", "start", "end"}:
                            el["category"] = cato
                            GradingElement.objects.create(**el)
        return redirect("tournament:grading")
