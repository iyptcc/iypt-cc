from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, UpdateView
from django_downloadview import ObjectDownloadView

from apps.account.models import ActiveUser
from apps.bank.models import Account, Payment
from apps.bank.utils import get_subpayments
from apps.plan.utils import _normal_capitalisation
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf, render_to_pdf_local
from apps.printer.utils import _get_next_pdfname
from apps.registration.models import UserProperty, UserPropertyValue
from apps.tournament.models import Tournament

from .forms import AccountAddressForm, ProfileForm, SkinForm, TournamentForm, UserPropertyForm
from .models import Attendee

# Create your views here.

@method_decorator(login_required, name='dispatch')
class TournamentView(View):

    def get(self, request):

        allperm = request.user.get_all_permissions()

        form = TournamentForm(instance=request.user.profile)

        skin = None
        if request.user.profile.tournament:
            skin = SkinForm(instance=request.user.profile.active)

        roles = []
        try:
            roles = request.user.profile.active.roles.all()
        except:
            pass

        return render(request, "account/tournament.html",{'form':form, 'permissions':allperm,'roles':roles,"skin":skin})

    #@method_decorator(permission_required('account.change_activeuser'))
    def post(self, request):

        if "_skin" in request.POST:
            skin = SkinForm(request.POST, instance=request.user.profile.active)
            if skin.is_valid():
                skin.save()

            form = TournamentForm(instance=request.user.profile)
        else:
            form = TournamentForm(request.POST, instance=request.user.profile)
            if form.is_valid():
                form.save()
                if request.user.profile.active:
                    messages.add_message(request, messages.SUCCESS, "Changed to {}".format(request.user.profile.active.tournament))
                else:
                    messages.add_message(request, messages.WARNING, "Unset active tournament, plase apply for participation or select tournament")
            skin = SkinForm(instance=request.user.profile.active)

        return redirect("account:tournament")

@method_decorator(login_required, name='dispatch')
class ProfileView(View):

    def get(self, request):
        form = ProfileForm(request.user.profile)
        form.fields["avatar"].initial = request.user.profile.avatar
        upform = UserPropertyForm(request.user.profile)

        name = "%s %s" % (request.user.first_name, request.user.last_name)
        cap = _normal_capitalisation(name)
        print(cap)

        return render(request,"account/profile.html", context={"form":form, "upform": upform, 'chars': form.allowed_chars(), "name":name, "cap":not cap})

    def post(self, request):

        if '_settings' in request.POST:
            form = ProfileForm(request.user.profile, request.POST, request.FILES)
            upform = UserPropertyForm(request.user.profile)

            if form.is_valid():
                request.user.first_name = form.cleaned_data["first_name"]
                request.user.last_name = form.cleaned_data["last_name"]
                request.user.save()
                f = request.FILES.get("avatar", None)
                if f or form.cleaned_data["avatar"]==False:
                    request.user.profile.avatar = f
                    request.user.profile.save()

                return redirect("account:profile")

        if '_profile' in request.POST:
            form = ProfileForm(request.user.profile)
            upform = UserPropertyForm(request.user.profile, request.POST)

            if upform.is_valid():

                upform.save(request)

                return redirect("account:profile")

        return render(request, "account/profile.html", context={"form": form, "upform":upform, 'chars': form.allowed_chars()})


@method_decorator(login_required, name='dispatch')
class AvatarView(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        try:
            obj = self.request.user.profile.avatar
            return obj
        except:
            raise ActiveUser.DoesNotExist("Avatar does not exist")

@method_decorator(login_required, name='dispatch')
class AccountsView(ListView):

    template_name = "account/accounts.html"

    def get_queryset(self):

        trn = self.request.user.profile.tournament
        acs = []
        for ac in Account.objects.filter(owners__tournament=trn, owners=self.request.user.profile.active).distinct():
            inp, iamt, ipend = get_subpayments(
                Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn,
                                       residual_of__isnull=True).filter(receiver=ac).distinct())

            inp, oamt, opend = get_subpayments(
                Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn,
                                       residual_of__isnull=True).filter(Q(sender=ac)).distinct())

            acs.append({"account":ac, "balance": iamt - ipend - (oamt - opend) , "balance_pending":ipend - opend})

        return acs

@method_decorator(login_required, name='dispatch')
class AccountView(UpdateView):

    template_name = "account/account.html"

    form_class = AccountAddressForm

    def get_success_url(self):
        return reverse("account:list_account", kwargs={"account":self.object.id})

    def get_object(self, queryset=None):
        obj = get_object_or_404(Account, owners=self.request.user.profile.active,
                                id=self.kwargs['account'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        trn = self.request.user.profile.tournament

        context["id"] = self.kwargs["account"]

        context["account"] = Account.objects.get(id=self.kwargs['account'],owners=self.request.user.profile.active)

        inp, iamt, ipend = get_subpayments(Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn, residual_of__isnull=True).filter(receiver_id=self.kwargs['account']).distinct())

        context["incomming"] = inp
        context["incomming_sum"] = iamt
        context["incomming_pend"] = ipend

        inp, oamt, opend = get_subpayments(
            Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn,
                                   residual_of__isnull=True).filter(Q(sender_id=self.kwargs['account'])).distinct())

        context["outgoing"] = inp
        context["outgoing_sum"] = oamt
        context["outgoing_pend"] = opend

        context["balance"] = iamt-ipend - (oamt-opend)
        context["balance_pending"] = ipend - opend

        context["pdfs"] = context["account"].pdf_set.all()

        return context

@login_required
def geninvoice(request, a_id):

    if request.method == "POST" or True:
        trn = request.user.profile.tournament
        acc = get_object_or_404(Account, pk=a_id, owners=request.user.profile.active)

        context = context_generator.invoice(acc, request.user.profile.active)

        fileprefix="invoice-account-%d-v"%(acc.id)

        pdf = Pdf.objects.create(name="%s%d"%(fileprefix,_get_next_pdfname(trn,fileprefix)), tournament=trn)
        pdf.invoice_account = acc
        pdf.save()

        res = render_to_pdf.delay(trn.default_templates.get(type=Template.INVOICE).id, pdf.id, context=context)

        pdf.task_id = res.id
        pdf.save()

        if PdfTag.objects.filter(tournament=trn, type=Template.INVOICE).exists():
            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.INVOICE))

        return redirect("account:list_account", account=acc.id)


@method_decorator(login_required, name='dispatch')
class InvoiceView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            acc = get_object_or_404(Account, pk=self.kwargs['a_id'], owners=self.request.user.profile.active)
            obj = acc.pdf_set.get(id=self.kwargs['pdf_id']).file
            return obj
        except:
            raise Pdf.DoesNotExist("File does not exist")
