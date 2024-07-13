from django import forms
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import redirect, reverse
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from formtools.preview import FormPreview

from apps.dashboard.forms import ModelDeleteListField


class ListPreview(FormPreview):

    form_template = None
    preview_template = "dashboard/previewObjsDelete.html"

    success_url = None

    class DirectSelector(object):

        def __init__(self, id, name):
            self.id = id
            self.name = name

        def __str__(self):
            return "%s" % self.name

    def get_filters(self, reqest):
        return []

    def get_queryset(self):
        raise NotImplementedError("Must subclass get_queryset")

    def get_prefetch(self):
        return []

    def obj_data(self, obj_list):
        return obj_list

    def form_members(self):
        return {}

    def require_objs(self):
        return True

    def parse_params(self, request):

        self.filters = self.get_filters(request)
        for fil in self.filters:
            if not "filter_name" in fil:
                fil["filter_name"] = fil["filter"]

        self.request = request

        self._filters = {}
        self._excludes = {}

        for fname in [x["filter"] for x in self.filters if "filter" in x]:
            try:
                inarg = request.GET.getlist("in_%s" % fname, None)
                if len(inarg) > 0:
                    try:
                        self._filters[fname] = list(map(int, inarg))
                    except:
                        self._filters[fname] = list(inarg)
                exarg = request.GET.getlist("ex_%s" % fname, None)
                if len(exarg) > 0:
                    try:
                        self._excludes[fname] = list(map(int, exarg))
                    except:
                        self._excludes[fname] = list(exarg)
            except:
                pass

        ex_query = Q()

        for k in self._excludes:
            ex_query |= Q(**{k: self._excludes[k]})

        qs = (
            self.get_queryset()
            .filter(**self._filters)
            .exclude(ex_query)
            .distinct()
            .prefetch_related(*self.get_prefetch())
        )

        filterfuncs = [x for x in self.filters if "filter_func" in x]
        if len(filterfuncs):
            ids = list(qs.values_list("id", flat=True))
            for ff in filterfuncs:
                try:
                    inarg = request.GET.getlist("in_%s" % ff["filter_name"], None)
                    if len(inarg) > 0:
                        self._filters[ff["filter_name"]] = list(map(int, inarg))
                        for obj in qs:
                            funcval = ff["filter_func"](obj)
                            if type(funcval) == list:
                                if all(
                                    [fv not in list(map(int, inarg)) for fv in funcval]
                                ):
                                    if obj.id in ids:
                                        ids.remove(obj.id)
                            else:
                                if funcval not in list(map(int, inarg)):
                                    if obj.id in ids:
                                        ids.remove(obj.id)

                    exarg = request.GET.getlist("ex_%s" % ff["filter_name"], None)
                    if len(exarg) > 0:
                        self._excludes[ff["filter_name"]] = list(map(int, exarg))
                        for obj in qs:
                            funcval = ff["filter_func"](obj)
                            if type(funcval) == list:
                                if any([fv in list(map(int, exarg)) for fv in funcval]):
                                    if obj.id in ids:
                                        ids.remove(obj.id)
                            else:
                                if funcval in list(map(int, exarg)):
                                    if obj.id in ids:
                                        ids.remove(obj.id)
                except Exception as e:
                    print(e)
                    pass

            qs = qs.filter(id__in=ids)
        self.obj_list = ModelDeleteListField(queryset=qs, required=self.require_objs())

        membervars = {"obj_list": self.obj_list}
        membervars.update(self.form_members())
        self.form = type("ObjsForm", (forms.Form,), membervars)

    def get_context(self, request, form):

        filters = []

        for fil in self.filters:
            f = {
                "name": fil["name"],
                "elements": fil["elements"],
                "link_name": fil["filter_name"],
            }

            # f['active'] = self.filter.get(f['link_name'], None)

            filter_rest = "&".join(
                [
                    "&".join(["in_%s=%s" % (f, g) for g in self._filters[f]])
                    for f in self._filters
                    if f != fil["filter_name"]
                ]
            )

            exclude_rest = "&".join(
                [
                    "&".join(["ex_%s=%s" % (f, g) for g in self._excludes[f]])
                    for f in self._excludes
                    if f != fil["filter_name"]
                ]
            )

            f["link_rest"] = "&".join([filter_rest, exclude_rest])

            f["in_actives"] = self._filters.get(fil["filter_name"], [])
            f["ex_actives"] = self._excludes.get(fil["filter_name"], [])

            filters.append(f)

        return {
            "filters": filters,
            "form": form,
            "stage_field": self.unused_name("stage"),
            "state": self.state,
        }

    def preview_actions(self, request, form, context):
        pass

    def done_actions(self, request, cleaned_data):
        pass

    def delete_perm(self, request):
        return True

    def process_preview(self, request, form, context):

        if "_delete" in request.POST:
            context["action"] = "_delete"

            self.preview_template = "dashboard/previewObjsDelete.html"

            def format_callback(obj):
                return "%s: %s" % (capfirst(obj._meta.verbose_name), obj)

            ps = form.cleaned_data["obj_list"]
            collector = NestedObjects(using="default")  # or specific database
            collector.collect(ps)
            to_delete = collector.nested(format_callback)

            context["objs"] = to_delete

        else:
            self.preview_actions(request, form, context)

    def done(self, request, cleaned_data):

        ps = cleaned_data["obj_list"]

        if "action" not in request.POST:
            if self.delete_perm(request):
                ps.model.objects.filter(id__in=ps.values("id")).delete()

        else:
            ret = self.done_actions(request, cleaned_data)
            if ret is not None:
                return ret

        return redirect(reverse(self.success_url) + "?" + request.GET.urlencode())
