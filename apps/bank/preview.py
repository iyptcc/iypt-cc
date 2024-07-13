from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from formtools.preview import FormPreview

from .models import Account


@method_decorator(login_required, name="__call__")
class MergePreview(FormPreview):

    form_template = "bank/merge.html"
    preview_template = "bank/mergePreview.html"

    def parse_params(self, request, account):

        trn = request.user.profile.tournament

        try:
            self.account = (
                Account.objects.filter(id=account, owners__tournament=trn)
                .distinct()
                .get()
            )
        except:
            raise PermissionError()

        accfield = forms.ModelChoiceField(
            queryset=Account.objects.filter(owners__tournament=trn)
            .exclude(id=account)
            .distinct()
        )

        self.form = type("AccountForm", (forms.Form,), {"account": accfield})

    def get_context(self, request, form):

        return {
            "account": self.account,
            "form": form,
            "stage_field": self.unused_name("stage"),
            "state": self.state,
        }

    def process_preview(self, request, form, context):

        account = form.cleaned_data["account"]
        context["mergeaccount"] = account

        inp = []
        for p in account.incoming_payments.all():
            p.receiver = self.account
            inp.append(p)
        oup = []
        for p in account.outgoing_payments.all():
            p.sender = self.account
            oup.append(p)

        context["incomming"] = inp
        context["outgoing"] = oup

    def done(self, request, cleaned_data):

        acc = cleaned_data["account"]

        for p in acc.incoming_payments.all():
            p.receiver = self.account
            p.save()
        for p in acc.outgoing_payments.all():
            p.sender = self.account
            p.save()

        acc.delete()

        return redirect("bank:accounts")
