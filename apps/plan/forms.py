from django import forms
from django_select2.forms import Select2MultipleWidget, Select2Widget

from apps.account.models import Attendee, ParticipationRole
from apps.dashboard.datetimefield import DateTimeFieldNonTZ
from apps.dashboard.datetimepicker import DateTimePicker
from apps.plan.models import Event, TeamPlaceholder
from apps.team.models import Team, TeamRole
from apps.tournament.models import Origin, ScheduleTemplate, Tournament


class CuriieForm(forms.Form):

    input = forms.CharField(widget=forms.Textarea)
    default = forms.CharField(label="Default Country for Jurors")


class TeamDrawForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super(TeamDrawForm, self).__init__(*args, **kwargs)

        remteams = Team.competing.filter(tournament=tournament).prefetch_related(
            "origin"
        )

        self.placeholders = {}

        for pht in TeamPlaceholder.objects.filter(tournament=tournament):
            self.fields["phteam-%d" % pht.pk] = forms.ModelChoiceField(
                queryset=remteams,
                widget=Select2Widget,
                label=pht.name,
                initial=pht.team_id,
                required=False,
            )
            self.placeholders["phteam-%d" % pht.pk] = pht

    def clean(self):
        cleaned_data = super(self.__class__, self).clean()

        new = []
        for k in cleaned_data:
            if cleaned_data[k]:
                new.append(cleaned_data[k].pk)

        if len(new) != len(set(new)):
            raise forms.ValidationError("Team can only be assigned to 1 placeholder")


class TeamForm(forms.Form):
    def __init__(self, tournament, team, *args, **kwargs):
        super(TeamForm, self).__init__(*args, **kwargs)

        origin = Origin.objects.filter(tournament=tournament)

        persons = Attendee.objects.filter(
            tournament=tournament,
            teammember__isnull=True,
            roles__type=ParticipationRole.STUDENT,
        )

        captain = forms.ModelChoiceField(persons, widget=Select2Widget, required=False)
        self.fields["captain"] = captain
        try:
            if team:
                captain.initial = persons.get(
                    team=team, teammember__role=TeamRole.CAPTAIN
                )
        except:
            pass


class EventEditForm(forms.ModelForm):

    def __init__(self, trn: Tournament, *args, **kwargs):
        super(EventEditForm, self).__init__(*args, **kwargs)
        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            tz = trn.timezone
            if not tz == None:
                opts["timeZone"] = tz
        except:
            pass

        self.fields["time_start"].widget = DateTimePicker(
            format="%Y-%m-%dT%H:%M%z", options=opts
        )
        self.fields["time_end"].widget = DateTimePicker(
            format="%Y-%m-%dT%H:%M%z", options=opts
        )

    class Meta:
        model = Event
        fields = ["name", "type", "public", "time_start", "time_end"]

        field_classes = {
            "time_start": DateTimeFieldNonTZ,
            "time_end": DateTimeFieldNonTZ,
        }
