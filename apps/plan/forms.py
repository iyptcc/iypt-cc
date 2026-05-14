import csv
import hashlib
from difflib import SequenceMatcher

from django import forms
from django.contrib.auth.models import User
from django_select2.forms import Select2MultipleWidget, Select2Widget

from apps.account.models import ActiveUser, Attendee, ParticipationRole
from apps.dashboard.datetimefield import DateTimeFieldNonTZ
from apps.dashboard.datetimepicker import DateTimePicker
from apps.plan.models import Event, TeamPlaceholder
from apps.team.models import Team, TeamRole
from apps.tournament.models import Origin, ScheduleTemplate, Tournament


class CuriieForm(forms.Form):

    input = forms.CharField(widget=forms.Textarea)
    default = forms.CharField(label="Default Country for Jurors")


class UserChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, match_scores=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.match_scores = match_scores or {}

    def label_from_instance(self, obj: ActiveUser):
        score = self.match_scores.get(obj.pk, 0)
        return f"{obj.user.first_name} {obj.user.last_name} <{obj.user.email}> ({score:.2f}) part in: {','.join(map(str,obj.tournaments.all()))}"


class AttendeeCreateImportForm(forms.Form):

    def row_key(self, row):
        base = str(row)
        return hashlib.sha224(base.encode()).hexdigest()[:20]

    def __init__(self, tournament, *args, **kwargs):

        data = args[0] if args else None

        if data:
            data = data.copy()

        dynamic_fields = {}
        if len(args) > 0:
            post = args[0]
            if "input" in post:
                # print(post["input"])
                reader = csv.DictReader(post["input"].splitlines())
                headers = []
                for row in reader:
                    headers = list(row.keys())
                    break

                dynamic_fields["first_name_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers), widget=Select2Widget
                )
                dynamic_fields["last_name_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers), widget=Select2Widget
                )
                dynamic_fields["email_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers),
                    required=False,
                    widget=Select2Widget,
                )
                # print("kwargs", kwargs)

                if "first_name_column" in post and "last_name_column" in post:
                    reader = csv.DictReader(post["input"].splitlines())

                    all_names = ActiveUser.objects.all()
                    # print(all_names)
                    for row in reader:
                        lno = self.row_key(row)
                        first_name = row[post["first_name_column"]].strip()
                        last_name = row[post["last_name_column"]].strip()
                        email = post["default_email"]
                        if "email_column" in post and post["email_column"]:
                            email = row.get(post["email_column"], "").strip()
                            if not len(email):
                                email = post["default_email"]
                        # print(first_name, last_name)
                        matches = []
                        scores = {}
                        for exist in all_names:
                            fsim = SequenceMatcher(
                                None, exist.user.first_name, first_name
                            )
                            lsim = SequenceMatcher(
                                None, exist.user.last_name, last_name
                            )
                            fr = fsim.ratio()
                            lr = lsim.ratio()
                            if (fr > 0.5 and lr > 0.5) or email == exist.user.email:
                                # print(exist)
                                matches.append(exist.id)
                                scores[exist.id] = fr + lr

                        if len(scores.values()):
                            if data and f"user_{lno}" not in data:

                                data[f"user_{lno}"] = str(max(scores, key=scores.get))

                            best_id = max(scores, key=scores.get)
                            already_in = all_names.filter(
                                pk=best_id, tournaments=tournament
                            ).exists()
                            # print("in", already_in)
                            if data and f"import_{lno}" not in data:
                                data[f"import_{lno}"] = str(not already_in)
                        else:
                            if data and f"import_{lno}" not in data:
                                data[f"import_{lno}"] = str(True)

                        dynamic_fields[f"user_{lno}"] = UserChoiceField(
                            queryset=ActiveUser.objects.filter(pk__in=matches),
                            required=False,
                            match_scores=scores,
                            widget=Select2Widget,
                            label=f"{first_name} {last_name} <{email}> matches",
                        )
                        dynamic_fields[f"import_{lno}"] = forms.BooleanField(
                            required=False, label=f"import {first_name} {last_name}"
                        )

        if data:
            args = (data,)

        super(AttendeeCreateImportForm, self).__init__(*args, **kwargs)

        self.fields["input"] = forms.CharField(widget=forms.Textarea)
        self.fields["default_email"] = forms.CharField()
        self.fields["assigned_role"] = forms.ModelChoiceField(
            queryset=ParticipationRole.objects.filter(tournament=tournament)
        )

        self.fields.update(dynamic_fields)


class TeamCreateImportForm(forms.Form):

    def row_key(self, row):
        base = str(row)
        return hashlib.sha224(base.encode()).hexdigest()[:20]

    def __init__(self, tournament, *args, **kwargs):

        data = args[0] if args else None

        if data:
            data = data.copy()

        dynamic_fields = {}
        if len(args) > 0:
            post = args[0]
            if "input" in post:
                # print(post["input"])
                reader = csv.DictReader(post["input"].splitlines())
                headers = []
                for row in reader:
                    headers = list(row.keys())
                    break

                dynamic_fields["first_name_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers), widget=Select2Widget
                )
                dynamic_fields["last_name_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers), widget=Select2Widget
                )
                dynamic_fields["team_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers), widget=Select2Widget
                )
                dynamic_fields["role_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers), widget=Select2Widget
                )
                dynamic_fields["problem_column"] = forms.ChoiceField(
                    choices=((s, s) for s in headers),
                    widget=Select2Widget,
                    required=False,
                )

                if "role_column" in post:
                    reader = csv.DictReader(post["input"].splitlines())
                    roleset = set()
                    for row in reader:
                        role = row[post["role_column"]].strip()
                        roleset.add(role)
                    for role in roleset:
                        dynamic_fields[f"role_{self.row_key(role)}"] = (
                            forms.ModelChoiceField(
                                queryset=tournament.teamrole_set.all(),
                                label=f"{role} matches",
                            )
                        )

                if "team_column" in post:
                    reader = csv.DictReader(post["input"].splitlines())
                    teamset = set()
                    for row in reader:
                        team = row[post["team_column"]].strip()
                        teamset.add(team)

                    for team in teamset:

                        all_origins: list[Origin] = tournament.origin_set.all()
                        matches = []
                        scores = {}
                        for exist in all_origins:
                            sim = SequenceMatcher(None, exist.name, team)
                            r = sim.ratio()
                            if r > 0.5:
                                # print(exist)
                                matches.append(exist.id)
                                scores[exist.id] = r

                        if len(scores.values()):
                            if data and f"team_{self.row_key(team)}" not in data:
                                data[f"team_{self.row_key(team)}"] = str(
                                    max(scores, key=scores.get)
                                )

                        dynamic_fields[f"team_{self.row_key(team)}"] = (
                            forms.ModelChoiceField(
                                queryset=tournament.origin_set.filter(pk__in=matches),
                                required=False,
                                widget=Select2Widget,
                                label=f"{team} matches",
                            )
                        )

                if all([f in post for f in ["first_name_column", "last_name_column"]]):
                    reader = csv.DictReader(post["input"].splitlines())

                    all_names: list[Attendee] = tournament.attendee_set.all()
                    # print(all_names)
                    for row in reader:
                        lno = self.row_key(row)
                        first_name = row[post["first_name_column"]].strip()
                        last_name = row[post["last_name_column"]].strip()
                        # print(first_name, last_name)
                        matches = []
                        scores = {}
                        for exist in all_names:
                            fsim = SequenceMatcher(None, exist.first_name, first_name)
                            lsim = SequenceMatcher(None, exist.last_name, last_name)
                            fr = fsim.ratio()
                            lr = lsim.ratio()
                            if fr > 0.5 and lr > 0.5:
                                # print(exist)
                                matches.append(exist.id)
                                scores[exist.id] = fr + lr

                        if len(scores.values()):
                            if data and f"member_{self.row_key(row)}" not in data:
                                data[f"member_{self.row_key(row)}"] = str(
                                    max(scores, key=scores.get)
                                )

                        dynamic_fields[f"member_{self.row_key(row)}"] = (
                            forms.ModelChoiceField(
                                queryset=tournament.attendee_set.filter(pk__in=matches),
                                widget=Select2Widget,
                                label=f"{first_name} {last_name} matches",
                            )
                        )
        if data:
            args = (data,)

        super(TeamCreateImportForm, self).__init__(*args, **kwargs)

        self.fields["input"] = forms.CharField(widget=forms.Textarea)

        self.fields.update(dynamic_fields)


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
