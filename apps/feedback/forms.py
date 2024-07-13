from django import forms

from .models import ChairFeedback, ChairFeedbackGrade, Feedback


class JurorFeedbackForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(JurorFeedbackForm, self).__init__(*args, **kwargs)
        if hasattr(self.instance, "jurorsession"):
            self.fields["grade"].label = (
                "Grade for %s" % self.instance.jurorsession.juror.attendee.full_name
            )
            self.fields["grade"].queryset = (
                self.instance.jurorsession.juror.attendee.tournament.feedbackgrade_set.all()
            )
        elif "initial" in kwargs:
            self.fields["grade"].label = (
                "Grade for %s" % self.initial["jurorsession"].juror.attendee.full_name
            )
            self.fields["grade"].queryset = self.initial[
                "jurorsession"
            ].juror.attendee.tournament.feedbackgrade_set.all()
            self.instance.jurorsession = self.initial["jurorsession"]
            self.instance.team = self.initial["team"]

    class Meta:
        model = Feedback
        fields = ("grade", "comment")

        widgets = {"comment": forms.Textarea, "grade": forms.RadioSelect}


class ChairFeedbackForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        trn = kwargs.pop("tournament")
        super().__init__(*args, **kwargs)
        for cr in trn.chairfeedbackcriterion_set.all():
            try:
                grade = self.instance.chairfeedbackgrade_set.get(criterion=cr).grade
            except ChairFeedbackGrade.DoesNotExist:
                grade = None
            except ValueError:
                grade = None
            self.fields["chair-criterion-%d" % cr.id] = forms.ModelChoiceField(
                trn.feedbackgrade_set.all(),
                widget=forms.RadioSelect,
                label=cr.name,
                required=False,
                initial=grade,
            )
            self.fields["chair-criterion-%d" % cr.id].criterion = cr

        if hasattr(self.instance, "jurorsession"):
            self.fields["comment"].label = (
                "Comment for %s" % self.instance.jurorsession.juror.attendee.full_name
            )
        elif "initial" in kwargs:
            self.fields["comment"].label = (
                "Comment for %s" % self.initial["jurorsession"].juror.attendee.full_name
            )
            self.instance.jurorsession = self.initial["jurorsession"]
            self.instance.team = self.initial["team"]

    class Meta:
        model = ChairFeedback
        fields = ("comment",)

    def save(self, commit=True):
        feedback = super().save(commit=False)
        if commit:
            feedback.save()

            for field in self.changed_data:
                if field == "comment":
                    continue
                ChairFeedbackGrade.objects.update_or_create(
                    feedback=self.instance,
                    criterion=self.fields[field].criterion,
                    defaults={"grade": self.cleaned_data[field]},
                )
