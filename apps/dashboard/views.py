from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import TemplateView
from django_downloadview import ObjectDownloadView

from apps.tournament.models import Origin, Tournament

from .forms import SimpleloginForm


class BaseView(TemplateView):
    __instance = None

    @classmethod
    def replace_with(cls, instance):
        cls.__instance = instance

    @classmethod
    def instance(cls):
        return cls.__instance or cls


class MessageView(BaseView):
    template_name = 'dashboard/base-layout.html'

    def get(self, request, *args, **kwargs):
        messages.debug(request, 'Redefine this page')
        return render(request, self.template_name)


class NotificationView(BaseView):
    template_name = 'dashboard/base-layout.html'

    def get(self, request, *args, **kwargs):
        messages.debug(request, 'Redefine this page')
        return render(request, self.template_name)


class TaskView(BaseView):
    template_name = 'dashboard/base-layout.html'

    def get(self, request, *args, **kwargs):
        messages.debug(request, 'Redefine this page')
        return render(request, self.template_name)


def index(request):
    return HttpResponseNotAllowed([])

def openmenu(request, uid):
    request.session['menu-display-%d'%int(uid)]=True
    return HttpResponse("")

def closemenu(request, uid):
    request.session['menu-display-%d'%int(uid)]=False
    return HttpResponse("")

def collapsemenu(request, opt):
    if opt=='on':
        request.session['collapsedmenu'] = True
    else:
        request.session['collapsedmenu'] = False
    return HttpResponse("")

class Simplelogin(View):

    def get(self, request, t_slug):

        trn = get_object_or_404(Tournament, slug=t_slug, results_access=Tournament.RESULTS_PASSWORD)

        form = SimpleloginForm(trn)

        return render(request, "dashboard/user/simplelogin.html", context={"form":form})

    def post(self, request, t_slug):

        trn = get_object_or_404(Tournament, slug=t_slug, results_access=Tournament.RESULTS_PASSWORD)

        form = SimpleloginForm(trn, request.POST)

        if form.is_valid():
            request.session["results-auth-%s"%trn.slug]=True

            return redirect("result:plan", t_slug=t_slug)

        return render(request, "dashboard/user/simplelogin.html", context={"form":form})

def simplelogout(request):

    for t in Tournament.objects.filter(results_access=Tournament.RESULTS_PASSWORD):
        request.session["results-auth-%s" % t.slug] = False

    return redirect("result:index")

@login_required
def password_change_done(request,
                         template_name='dashboard/password_change_form.html',
                         extra_context=None):

    messages.success(request, _('Password change successful'))
    # {% _('Your password was changed.') %}

    # context = {
    #     'title': _('Password change successful'),
    # }
    # if extra_context is not None:
    #     context.update(extra_context)
    #
    # return TemplateResponse(request, template_name, context)

class FlagImageView(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        try:
            ori = Origin.objects.get(tournament__slug=self.kwargs["t_slug"], slug=self.kwargs["o_slug"])
            if ori.flag:
                return ori.flag

        except Exception as e:
            print(e)
            raise Origin.DoesNotExist("Image does not exist")
