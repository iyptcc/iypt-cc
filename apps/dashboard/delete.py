from django.contrib.admin.utils import NestedObjects
from django.shortcuts import redirect, render
from django.utils.text import capfirst
from django.views import View

from apps.jury.models import JurorGrade


class ConfirmedDeleteView(View):

    redirection = "tournament:problems"

    def get_redirection(self, request, *args, **kwargs):
        return redirect(self.redirection)

    def get_objects(self, request, *args, **kwargs):
        raise NotImplemented("You must implement this function")

    def get(self, request, *args, **kwargs):

        # pr = get_object_or_404(Problem, tournament=request.user.profile.tournament, id=id)

        objs = self.get_objects(request, *args, **kwargs)

        def format_callback(obj):
            # print("callbacked %s"%(capfirst(obj._meta.verbose_name),) )
            #
            if type(obj) == JurorGrade:
                return "%s" % (capfirst(obj._meta.verbose_name),)
            else:
                return "%s: %s" % (capfirst(obj._meta.verbose_name), obj)

        collector = NestedObjects(using="default")  # or specific database
        if type(objs) == list:
            for obj in objs:
                print("process list item", obj)
                collector.collect([obj])
            to_delete = collector.nested(format_callback)
        else:
            collector.collect(objs)
            to_delete = collector.nested(format_callback)

        return render(
            request, "dashboard/delObjPreview.html", context={"objs": to_delete}
        )

    def post(self, request, *args, **kwargs):
        objs = self.get_objects(request, *args, **kwargs)
        if type(objs) == list:
            for obj in objs:
                obj.delete()
        else:
            objs.delete()

        return self.get_redirection(request, *args, **kwargs)
