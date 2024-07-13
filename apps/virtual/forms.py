from django import forms
from django.utils.html import format_html_join
from django_select2.forms import Select2MultipleWidget, Select2Widget

from ..tournament.models import Tournament
from .models import Hall, HallRole, Stream


class RoomsForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super(RoomsForm, self).__init__(*args, **kwargs)

        self.rs = []
        for round in tournament.round_set.all():
            r = []
            for fight in round.fight_set.select_related("room").all():
                server = forms.ModelChoiceField(
                    queryset=tournament.bbbinstance_set.all(),
                    widget=Select2Widget,
                    required=False,
                )
                server.fight = fight
                server.initial = fight.virtual_server
                r.append("%d-%d" % (round.order, fight.pk))
                self.fields["server-%d-%d" % (round.order, fight.pk)] = server

                rec = forms.BooleanField(required=False)
                rec.fight = fight
                rec.initial = fight.virtual_record
                self.fields["record-%d-%d" % (round.order, fight.pk)] = rec
            self.rs.append(r)

    def save(self):
        for cf in self.changed_data:
            if type(self.fields[cf]) == forms.ModelChoiceField:

                self.fields[cf].fight.virtual_server = self.cleaned_data[cf]
                self.fields[cf].fight.save()
            if type(self.fields[cf]) == forms.BooleanField:

                self.fields[cf].fight.virtual_record = self.cleaned_data[cf]
                self.fields[cf].fight.save()

    def rounds(self):
        for round in self.rs:
            yield [
                (
                    self.__getitem__("server-%s" % (name,)),
                    self.fields["server-%s" % name].fight,
                    self.__getitem__("record-%s" % (name,)),
                )
                for name in round
            ]


class HallEditForm(forms.ModelForm):

    def __init__(self, trn: Tournament, *args, **kwargs):
        super(HallEditForm, self).__init__(*args, **kwargs)
        self.fields["instance"].queryset = trn.bbbinstance_set.all()

    class Meta:
        model = Hall
        fields = [
            "name",
            "instance",
            "guest_policy",
            "mute_on_start",
            "allow_attendees_to_start_meeting",
            "lock_settings_disable_note",
            "lock_settings_disable_private_chat",
            "lock_settings_disable_cam",
            "record",
            "description",
        ]

        widgets = {
            "instance": Select2Widget(),
            "guest_policy": Select2Widget(),
        }


class HallRoleEditForm(forms.ModelForm):

    def __init__(self, trn, *args, **kwargs):
        super(HallRoleEditForm, self).__init__(*args, **kwargs)
        self.fields["role"].queryset = trn.participationrole_set.all()

    class Meta:
        model = HallRole
        fields = ["role", "mode"]

        widgets = {
            "role": Select2Widget(),
            "mode": Select2Widget(),
        }


class JurorGradeForm(forms.Form):

    def __init__(self, js, stage, *args, **kwargs):
        super(JurorGradeForm, self).__init__(*args, **kwargs)

        atts = [stage.rep_attendance, stage.opp_attendance]
        if stage.fight.round.review_phase:
            atts.append(stage.rev_attendance)

        self.partials = {}
        for att in atts:
            role = att.role.type
            f = forms.IntegerField(
                min_value=1,
                max_value=10,
                required=False,
                disabled=not stage.jurors_grading,
            )
            self.fields["grade_%s" % role] = f
            f.attendance = att
            try:
                f.initial_obj = att.jurorgrade_set.get(juror_session=js)
                f.initial = int(f.initial_obj.grade)
            except:
                pass

            self.partials[role] = []
            for gr in att.role.gradinggroup_set.all():
                f = forms.FloatField(
                    widget=forms.NumberInput(
                        attrs={
                            "type": "range",
                            "step": "0.1",
                            "min": gr.minimum,
                            "max": gr.maximum,
                        }
                    ),
                    min_value=gr.minimum,
                    max_value=gr.maximum,
                    required=False,
                    disabled=not stage.jurors_grading,
                )
                self.fields["partial_%d" % (gr.id)] = f
                f.gradinggroup = gr
                f.attendance = att
                try:
                    f.initial_obj = gr.groupgrade_set.get(
                        juror_session=js, stage_attendee=att
                    )
                    f.initial = f.initial_obj.value
                    init = f.initial_obj.value
                except:
                    f.initial = 0
                    init = 0
                    pass

                self.partials[role].append(
                    {
                        "name": gr.name,
                        "id": gr.id,
                        "min": gr.minimum,
                        "max": gr.maximum,
                        "initial": init,
                    }
                )

    def as_partials_table(self):
        tab = []
        for j in range(max([len(a) for a in self.partials.values()])):
            row = [""]
            for role in ["rep", "opp", "rev"]:
                if role not in self.partials.keys():
                    continue
                if len(self.partials[role]) > j:
                    row.append(
                        f'{self.partials[role][j]["name"]} ({self.partials[role][j]["min"]} – {self.partials[role][j]["max"]})'
                    )
                    row.append(self.partials[role][j]["id"])
                    row.append(self.partials[role][j]["initial"])
                    row.append(
                        self.__getitem__("partial_%d" % (self.partials[role][j]["id"]))
                    )
                else:
                    row += ["", "", "", ""]
            tab.append(row)

        if "rev" in self.partials:
            return format_html_join(
                "",
                "<tr><td>{}</td><td>{} <span style='font-weight:bold;' id='partial_value_{}'>{}</span> {}</td><td>{} <span  style='font-weight:bold;'  id='partial_value_{}'>{}</span> {}</td><td>{} <span  style='font-weight:bold;'  id='partial_value_{}'>{}</span> {}</td></tr>",
                tab,
            )
        else:
            return format_html_join(
                "",
                "<tr><td>{}</td><td>{} <span style='font-weight:bold;' id='partial_value_{}'>{}</span> {}</td><td>{} <span  style='font-weight:bold;'  id='partial_value_{}'>{}</span> {}</td></tr>",
                tab,
            )


class NameForm(forms.Form):

    name = forms.CharField(max_length=100)


class StreamEditForm(forms.ModelForm):

    def __init__(self, trn, *args, **kwargs):
        super(StreamEditForm, self).__init__(*args, **kwargs)
        self.fields["access"].queryset = trn.participationrole_set.all()

    class Meta:
        model = Stream
        fields = [
            "name",
            "access",
            "stream_name",
            "hls_format",
            "mpd_format",
            "external_link",
        ]

        widgets = {"access": Select2MultipleWidget()}
