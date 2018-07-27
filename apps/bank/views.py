from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render, reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.account.models import Attendee, ParticipationRole
from apps.dashboard.delete import ConfirmedDeleteView
from apps.team.models import Team

from .forms import AccountForm, PaymentForm, PropertyFeeForm, RoleFeeForm, SettlementForm, TeamFeeForm
from .models import Account, Payment, PropertyFee
from .utils import expected_fees, expected_person_fees, get_subpayments

# Create your views here.

class AccountsView(ListView):

    template_name = "bank/accounts.html"

    def get_queryset(self):

        trn = self.request.user.profile.tournament
        acs = []
        for ac in Account.objects.filter(owners__tournament=trn).distinct():
            inp, iamt, ipend = get_subpayments(
                Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn,
                                       residual_of__isnull=True).filter(receiver=ac).distinct())

            inp, oamt, opend = get_subpayments(
                Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn,
                                       residual_of__isnull=True).filter(Q(sender=ac)).distinct())

            acs.append({"account":ac, "balance": iamt - ipend - (oamt - opend) , "balance_pending":ipend - opend})

        return acs

class AccountCreateView(CreateView):

    template_name = "bank/account_form.html"

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return AccountForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    success_url = reverse_lazy("bank:accounts")

class AccountChangeView(UpdateView):
    template_name = "bank/account_form.html"

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return AccountForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def get_success_url(self):
        return reverse("bank:accounts")

    def get_object(self, queryset=None):
        obj = None
        try:
            obj = Account.objects.filter(owners__tournament=self.request.user.profile.tournament,
                                        id=self.kwargs['id']).distinct().first()
        except:
            pass
        if not obj:
            raise Http404
        return obj

class PaymentRequestView(CreateView):

    template_name = "bank/payment_form.html"

    success_url = reverse_lazy("bank:accounts")

    def get_form(self, form_class=None):

        return PaymentForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def form_valid(self, form):
        p = form.save(commit=False)
        p.created_by = self.request.user.profile.active
        p.save()
        form.save()
        return redirect("bank:accounts")

class AccountView(ListView):

    template_name = "bank/account.html"

    def get_queryset(self):
        trn = self.request.user.profile.tournament

        return Payment.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        trn = self.request.user.profile.tournament

        context["id"] = self.kwargs["account"]

        context["account"] = Account.objects.get(id=self.kwargs['account'])

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

        return context

class SettleView(View):
    def get(self, request, payment):

        trn = self.request.user.profile.tournament
        p = None
        try:
            p = Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn, id=payment, cleared_at__isnull=True, aborted_at__isnull=True).distinct().get()
            print(p)
        except:
            raise PermissionError()

        form = SettlementForm(instance=p)

        return render(request, "bank/settle.html",context={"payment":p, "form":form})

    def post(self, request, payment):

        trn = self.request.user.profile.tournament
        p = None
        try:
            p = Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn,
                                       id=payment, cleared_at__isnull=True, aborted_at__isnull=True).distinct().get()
            print(p)
        except:
            raise PermissionError("payment not found")

        old_amt = p.amount

        form = SettlementForm(request.POST, instance=p)

        if form.is_valid():
            new_amt = form.cleaned_data["amount"]
            settle = form.cleaned_data["mark_as_settled"]
            print(new_amt)
            if new_amt == old_amt:
                p.cleared_at = timezone.now()
                p.cleared_by = request.user.profile.active
                p.save()
                print("settled")
            elif new_amt < old_amt:
                r = Payment.objects.get(id=p.id)
                r.pk = None
                r.amount = old_amt - new_amt
                r.residual_of = p
                if settle:
                    r.aborted_at = timezone.now()
                    r.aborted_by = request.user.profile.active
                    r.abort_reason = form.cleaned_data["abort_reason"]
                r.save()

                p.cleared_at = timezone.now()
                p.cleared_by = request.user.profile.active
                p.amount = old_amt
                p.save()

                print("partially settled")
            else:
                print("payed more, settle 2")

            return redirect("bank:list_account",p.receiver_id)

        return render(request, "bank/settle.html", context={"payment": p, "form": form})

class TeamFeeView(UpdateView):
    template_name = "tournament/overview.html"

    form_class = TeamFeeForm

    def get_success_url(self):
        return reverse("bank:fee_team")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament

class RolesView(ListView):

    template_name = "bank/rolesList.html"

    def get_queryset(self):
        return ParticipationRole.objects.filter(tournament=self.request.user.profile.tournament)

class RoleFeeUpdate(UpdateView):
    template_name = "tournament/overview.html"

    form_class = RoleFeeForm

    def get_success_url(self):
        return reverse("bank:fee_roles")

    def get_object(self, queryset=None):
        obj = get_object_or_404(ParticipationRole, tournament=self.request.user.profile.tournament, id=self.kwargs['id'])
        return obj

class PFeeView(ListView):

    template_name = "bank/feeList.html"

    def get_queryset(self):
        return PropertyFee.objects.filter(tournament=self.request.user.profile.tournament)

class PFeeCreate(CreateView):

    template_name = "bank/propertyfee_form.html"

    success_url = reverse_lazy("bank:fee_property")

    def get_form(self, form_class=None):

        return PropertyFeeForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def form_valid(self, form):
        p = form.save(commit=False)
        p.tournament = self.request.user.profile.tournament
        p.save()
        form.save()
        return redirect("bank:fee_property")

class PFeeDelete(ConfirmedDeleteView):

    redirection = "bank:fee_property"

    def get_objects(self, request, *args, **kwargs):
        return PropertyFee.objects.filter(tournament=request.user.profile.tournament, id=kwargs["id"])

class TeamBill(View):

    def get(self, request):
        trn = request.user.profile.tournament
        teams = Team.objects.filter(tournament=self.request.user.profile.tournament)
        fees=[]
        for t in teams:
            team = {'obj':t}
            fee = expected_fees(t)
            feesum = sum([0] + [f["amount"] for f in fee])
            team["fee_sum"] = feesum

            total = 0
            team["accounts"] = []
            for ac in t.account_set.all():

                inp, oamt, opend = get_subpayments(
                    Payment.objects.filter(sender__owners__tournament=trn, receiver__owners__tournament=trn,
                                       residual_of__isnull=True).filter(Q(sender=ac)).distinct())

                team["accounts"].append({"account":ac, "o_sum":oamt, "o_pend":opend})
                total += oamt

            team["bill_differ"] = 0
            if total != feesum:
                team["bill_differ"]=feesum - total
            fees.append(team)

        return render(request,"bank/teams.html",context={"teams":fees})

class TeamFeeRequestView(CreateView):

    template_name = "bank/payment_form.html"

    success_url = reverse_lazy("bank:accounts")

    def get_form(self, form_class=None):

        accs = get_list_or_404(Account, team_id=self.kwargs["team"], team__tournament=self.request.user.profile.tournament)
        acc = None
        if len(accs) > 0:
            acc = accs[0]
        fee = expected_fees(get_object_or_404(Team, id=self.kwargs["team"], tournament=self.request.user.profile.tournament))
        feesum = sum([0] + [f["amount"] for f in fee])

        reference = ""
        for f in fee:
            reference+="%s : %.2lf\n"%(f["name"], f["amount"])

        return PaymentForm(self.request.user.profile.tournament, **{**self.get_form_kwargs(),"sender":acc,"amount":feesum,"reference":reference})

    def form_valid(self, form):
        p = form.save(commit=False)
        p.created_by = self.request.user.profile.active
        p.save()
        form.save()
        return redirect("bank:accounts")

class TeamAccountCreateView(CreateView):

    template_name = "bank/account_form.html"

    def get_form(self, form_class=None):

        team = get_object_or_404(Team, id=self.kwargs["team"], tournament=self.request.user.profile.tournament)
        return AccountForm(self.request.user.profile.tournament, **self.get_form_kwargs(),team=team, owners=team.get_managers())

    success_url = reverse_lazy("bank:bill_teams")

class AttendeeBill(View):

    def get(self, request):
        atts = Attendee.objects.filter(tournament=self.request.user.profile.tournament).prefetch_related("roles","active_user__user")
        fees=[]
        for att in atts:
            a = {"obj":att}
            a["accounts"] = att.account_set.all()
            fee = expected_person_fees(att)
            feesum = sum([0] + [f["amount"] for f in fee])
            a["fee_sum"] = feesum
            a["teams"] = att.team_set.all()
            fees.append(a)
        fees = sorted(fees,key=lambda x:len(x["teams"]))

        return render(request,"bank/attendees.html",context={"attendees":fees})

class AttendeeAccountCreateView(CreateView):

    template_name = "bank/account_form.html"

    def get_form(self, form_class=None):

        att = get_list_or_404(Attendee, id=self.kwargs["attendee"], tournament=self.request.user.profile.tournament)
        return AccountForm(self.request.user.profile.tournament, **self.get_form_kwargs(), owners=att)

    success_url = reverse_lazy("bank:bill_attendees")

class AttendeeFeeRequestView(CreateView):

    template_name = "bank/payment_form.html"

    success_url = reverse_lazy("bank:accounts")

    def get_form(self, form_class=None):

        accs = get_list_or_404(Account, owners__id=self.kwargs["attendee"], owners__tournament=self.request.user.profile.tournament)
        acc = None
        if len(accs) > 0:
            acc = accs[0]
        fee = expected_person_fees(get_object_or_404(Attendee, id=self.kwargs["attendee"], tournament=self.request.user.profile.tournament))
        feesum = sum([0] + [f["amount"] for f in fee])

        reference = ""
        for f in fee:
            reference+="%s : %.2lf\n"%(f["name"], f["amount"])

        return PaymentForm(self.request.user.profile.tournament, **{**self.get_form_kwargs(),"sender":acc,"amount":feesum,"reference":reference})

    def form_valid(self, form):
        p = form.save(commit=False)
        p.created_by = self.request.user.profile.active
        p.save()
        form.save()
        return redirect("bank:accounts")
