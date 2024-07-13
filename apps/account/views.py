from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, UpdateView
from django_downloadview import ObjectDownloadView
from mattermostdriver import Driver
from mattermostdriver.client import ResourceNotFound
from unidecode import unidecode

from apps.account.models import ActiveUser
from apps.bank.models import Account, Payment
from apps.bank.utils import get_subpayments
from apps.jury.models import Juror, JurorSession
from apps.plan.utils import _normal_capitalisation
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname

from ..plan.models import Round
from .forms import (
    AccountAddressForm,
    ProfileForm,
    SkinForm,
    TournamentForm,
    UserPropertyForm,
)


@method_decorator(login_required, name="dispatch")
class TournamentView(View):

    def get(self, request):

        allperm = request.user.get_all_permissions()

        form = TournamentForm(instance=request.user.profile)

        skin = None
        chat = False
        if request.user.profile.tournament:
            skin = SkinForm(instance=request.user.profile.active)
            chat = request.user.profile.tournament.allow_oauth

        roles = []
        try:
            roles = request.user.profile.active.roles.all()
        except AttributeError:
            pass

        return render(
            request,
            "account/tournament.html",
            {
                "form": form,
                "permissions": allperm,
                "roles": roles,
                "skin": skin,
                "chat": chat,
            },
        )

    # @method_decorator(permission_required('account.change_activeuser'))
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
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        "Changed to {}".format(request.user.profile.active.tournament),
                    )
                else:
                    messages.add_message(
                        request,
                        messages.WARNING,
                        "Unset active tournament, plase apply for participation or select tournament",
                    )
            skin = SkinForm(instance=request.user.profile.active)

        return redirect("account:tournament")


def mmusername(orig):
    out = ""
    mmalpha = [chr(i) for i in list(range(65, 65 + 26)) + list(range(97, 97 + 26))]
    mmlegal = mmalpha + [chr(i) for i in list(range(48, 48 + 10))] + [".", "-", "_"]
    for c in orig:
        decoded = unidecode(c)
        if decoded in mmlegal:
            out += decoded
        else:
            out += "_"
    if out[0] not in mmalpha:
        out = "c_" + out
    if len(out) < 3:
        out += "_padding"
    if len(out) > 22:
        out = out[:22]
    return out


@login_required
def mm_join(request):
    if request.method == "POST":
        try:
            trn = request.user.profile.tournament
        except Exception:
            messages.add_message(
                request, messages.ERROR, "You are not attending any Tournament"
            )
            return redirect("account:tournament")

        if trn.allow_oauth is False:
            messages.add_message(
                request, messages.ERROR, "The current Tournament does not use the chat."
            )
            return redirect("account:tournament")

        mm = Driver(
            {
                "url": settings.MM_URL,
                "token": settings.MM_TOKEN,
                "port": settings.MM_PORT,
            }
        )
        mm.login()
        teams = mm.teams.get_teams()
        if len(list(filter(lambda x: x["name"] == trn.slug, teams))) != 1:
            messages.add_message(
                request, messages.ERROR, "There is no Team for this Tournament"
            )
        else:
            # add user to team
            try:
                user = mm.users.get_user_by_email(request.user.email.lower())
            except ResourceNotFound:
                user = mm.users.create_user(
                    options={
                        "email": request.user.email,
                        "username": mmusername(request.user.username),
                        "first_name": request.user.first_name,
                        "last_name": request.user.last_name,
                        "auth_data": "%d" % request.user.id,
                        "auth_service": "gitlab",
                    }
                )
            team_id = list(filter(lambda x: x["name"] == trn.slug, teams))[0]["id"]
            mm.teams.add_user_to_team(
                team_id, options={"team_id": team_id, "user_id": user["id"]}
            )

            messages.add_message(
                request,
                messages.SUCCESS,
                "Added you to the chat team, you can log in at chat.iypt.org",
            )

        return redirect("account:tournament")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
class ProfileView(View):

    def get(self, request):
        form = ProfileForm(request.user.profile)
        form.fields["avatar"].initial = request.user.profile.avatar
        upform = UserPropertyForm(request.user.profile)

        name = "%s %s" % (request.user.first_name, request.user.last_name)
        cap = _normal_capitalisation(name)
        print(cap)

        return render(
            request,
            "account/profile.html",
            context={
                "form": form,
                "upform": upform,
                "chars": form.allowed_chars(),
                "name": name,
                "cap": not cap,
            },
        )

    def post(self, request):

        if "_settings" in request.POST:
            form = ProfileForm(request.user.profile, request.POST, request.FILES)
            upform = UserPropertyForm(request.user.profile)

            if form.is_valid():
                request.user.first_name = form.cleaned_data["first_name"]
                request.user.last_name = form.cleaned_data["last_name"]
                request.user.save()
                f = request.FILES.get("avatar", None)
                if f or form.cleaned_data["avatar"] is False:
                    request.user.profile.avatar = f
                    request.user.profile.save()

                return redirect("account:profile")

        if "_profile" in request.POST:
            form = ProfileForm(request.user.profile)
            upform = UserPropertyForm(request.user.profile, request.POST)

            if upform.is_valid():

                upform.save(request)

                return redirect("account:profile")

        return render(
            request,
            "account/profile.html",
            context={"form": form, "upform": upform, "chars": form.allowed_chars()},
        )


@method_decorator(login_required, name="dispatch")
class AvatarView(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        try:
            obj = self.request.user.profile.avatar
            return obj
        except AttributeError:
            raise ActiveUser.DoesNotExist("Avatar does not exist")


@login_required
def jurorplan(request):

    juror = get_object_or_404(Juror, attendee=request.user.profile.active)
    att = []
    ro: Round
    for ro in request.user.profile.tournament.round_set.all():
        sess = {"published": ro.publish_jurors, "round": ro}
        try:
            sess["att"] = juror.jurorsession_set.get(fight__round=ro)
        except JurorSession.DoesNotExist:
            sess["att"] = None
        if ro.reserved_jurors.filter(id=juror.id).exists():
            sess["reserve"] = True
        att.append(sess)
    return render(
        request,
        "jury/juror.html",
        context={
            "juror": juror,
            "attendences": att,
            "availability": request.user.profile.tournament.publish_juror_availability,
        },
    )


@method_decorator(login_required, name="dispatch")
class AccountsView(ListView):

    template_name = "account/accounts.html"

    def get_queryset(self):

        trn = self.request.user.profile.tournament
        acs = []
        for ac in Account.objects.filter(
            owners__tournament=trn,
            owners=self.request.user.profile.active,
            owners__isnull=False,
        ).distinct():
            inp, iamt, ipend = get_subpayments(
                Payment.objects.filter(
                    sender__owners__tournament=trn,
                    receiver__owners__tournament=trn,
                    residual_of__isnull=True,
                )
                .filter(receiver=ac)
                .distinct()
            )

            inp, oamt, opend = get_subpayments(
                Payment.objects.filter(
                    sender__owners__tournament=trn,
                    receiver__owners__tournament=trn,
                    residual_of__isnull=True,
                )
                .filter(Q(sender=ac))
                .distinct()
            )

            acs.append(
                {
                    "account": ac,
                    "balance": iamt - ipend - (oamt - opend),
                    "balance_pending": ipend - opend,
                }
            )

        return acs


@method_decorator(login_required, name="dispatch")
class AccountView(UpdateView):

    template_name = "account/account.html"

    form_class = AccountAddressForm

    def get_success_url(self):
        return reverse("account:list_account", kwargs={"account": self.object.id})

    def get_object(self, queryset=None):
        obj = get_object_or_404(
            Account,
            owners=self.request.user.profile.active,
            owners__isnull=False,
            id=self.kwargs["account"],
        )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        trn = self.request.user.profile.tournament

        context["id"] = self.kwargs["account"]

        context["account"] = Account.objects.get(
            id=self.kwargs["account"], owners=self.request.user.profile.active
        )

        inp, iamt, ipend = get_subpayments(
            Payment.objects.filter(
                sender__owners__tournament=trn,
                receiver__owners__tournament=trn,
                residual_of__isnull=True,
            )
            .filter(receiver_id=self.kwargs["account"])
            .distinct()
        )

        context["incomming"] = inp
        context["incomming_sum"] = iamt
        context["incomming_pend"] = ipend

        inp, oamt, opend = get_subpayments(
            Payment.objects.filter(
                sender__owners__tournament=trn,
                receiver__owners__tournament=trn,
                residual_of__isnull=True,
            )
            .filter(Q(sender_id=self.kwargs["account"]))
            .distinct()
        )

        context["outgoing"] = inp
        context["outgoing_sum"] = oamt
        context["outgoing_pend"] = opend

        context["balance"] = iamt - ipend - (oamt - opend)
        context["balance_pending"] = ipend - opend

        context["pdfs"] = context["account"].pdf_set.all()

        return context


@login_required
def geninvoice(request, a_id):

    if request.method == "POST" or True:
        trn = request.user.profile.tournament

        if trn.bank_generate_invoice:

            acc = get_object_or_404(
                Account,
                pk=a_id,
                owners=request.user.profile.active,
                owners__isnull=False,
            )

            context = context_generator.invoice(acc, request.user.profile.active)

            fileprefix = "invoice-account-%d-v" % (acc.id)

            pdf = Pdf.objects.create(
                name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
                tournament=trn,
            )
            pdf.invoice_account = acc
            pdf.save()

            res = render_to_pdf.delay(
                trn.default_templates.get(type=Template.INVOICE).id,
                pdf.id,
                context=context,
            )

            pdf.task_id = res.id
            pdf.save()

            if PdfTag.objects.filter(tournament=trn, type=Template.INVOICE).exists():
                pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.INVOICE))

            return redirect("account:list_account", account=acc.id)


@method_decorator(login_required, name="dispatch")
class InvoiceView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            acc = get_object_or_404(
                Account,
                pk=self.kwargs["a_id"],
                owners=self.request.user.profile.active,
                owners__isnull=False,
            )
            obj = acc.pdf_set.get(id=self.kwargs["pdf_id"]).file
            return obj
        except Pdf.DoesNotExist:
            raise Pdf.DoesNotExist("File does not exist")
