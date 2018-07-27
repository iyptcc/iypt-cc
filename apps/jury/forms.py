from django import forms
from django.db.models import Q
from django_select2.forms import Select2MultipleWidget, Select2Widget

from .models import Juror, JurorRole


class JurorForm(forms.ModelForm):

    class Meta:

        model = Juror

        fields = ["bias", "conflicting"]

        widgets = {"conflicting": Select2MultipleWidget()}

class JuryForm(forms.Form):

    chair = forms.ModelChoiceField(required=False, queryset=None, widget=Select2Widget)
    jurors = forms.ModelMultipleChoiceField(required=False, queryset=None, widget=Select2MultipleWidget)


    def __init__(self, fight, *args, **kwargs):
        super(JuryForm, self).__init__(*args, **kwargs)

        self.fields['chair'].queryset = Juror.objects.filter(
            (Q(attendee__tournament=fight.round.tournament) & ~Q(fights__round=fight.round))
            | Q(fights=fight)
            ).prefetch_related('attendee__active_user__user')\
            .distinct().order_by('attendee__active_user__user__last_name')
        try:
            self.fields['chair'].initial = fight.jurorsession_set(manager='chair').get().juror_id
        except:
            pass

        self.fields['jurors'].queryset = Juror.objects.filter(
            (Q(attendee__tournament=fight.round.tournament) & ~Q(fights__round=fight.round))
            | Q(fights=fight)
            ).prefetch_related('attendee__active_user__user')\
            .distinct().order_by('attendee__active_user__user__last_name')

        self.fields['jurors'].obj_initial=Juror.objects.filter(fights=fight,jurorsession__role__type=JurorRole.JUROR)
        self.fields['jurors'].initial = self.fields['jurors'].obj_initial.values_list('id',flat=True)

    def clean(self):
        cleaned_data = super(JuryForm, self).clean()
        chair = cleaned_data.get("chair")
        jurors = cleaned_data.get("jurors")

        if chair in jurors:
            raise forms.ValidationError("Chair must not be a juror.")

class AssignForm(forms.Form):

    rounds = forms.IntegerField(min_value=1, initial=1000)
    room_jurors = forms.IntegerField(min_value=2, initial=5)
    cooling_base = forms.FloatField(min_value=0, max_value=1, initial=0.99)
    fix_rounds = forms.IntegerField(min_value=0, initial=0)

class AcceptPossibleJurorForm(forms.Form):

    name = forms.CharField(max_length=200, disabled=True)
    email = forms.EmailField(max_length=200, disabled=True)

    experience = forms.ChoiceField(choices=Juror.EXPERIENCES)

    notify = forms.BooleanField(required=False, label="Notify Applicant", initial=True)

    def __init__(self, pJ, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].initial = "%s %s"%(pJ.person.user.first_name, pJ.person.user.last_name)
        self.fields["email"].initial = pJ.person.user.email
        self.fields["experience"].initial = pJ.experience
