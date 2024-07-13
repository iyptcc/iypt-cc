import os.path
from datetime import datetime
from stat import S_ISDIR, S_ISREG

from django import forms
from django.db import IntegrityError
from django.forms import ClearableFileInput
from django.utils.html import format_html_join
from django_select2.forms import Select2MultipleWidget, Select2Widget
from paramiko import SFTPClient
from PIL import Image

from apps.account.models import Attendee
from apps.jury.models import JurorSession
from apps.plan.models import FightRole
from apps.printer.models import Pdf, PdfTag
from apps.result.utils import _fightpreview
from apps.team.models import TeamRole
from apps.tournament.models import Origin, Problem, Tournament

from ..printer.forms import RemoteFile
from ..registration.utils import pdf_validator
from .utils import fight_grades_valid


class StageForm(forms.Form):

    def __init__(self, stage, *args, **kwargs):
        super(StageForm, self).__init__(*args, **kwargs)

        prev = _fightpreview(stage.fight)[stage.order - 1]
        if prev["pk"] != stage.pk:
            raise IntegrityError("Stage number integrity Error")

        self.fields["rejections"] = forms.ModelMultipleChoiceField(
            queryset=Problem.objects.filter(tournament=stage.fight.round.tournament),
            required=False,
            widget=Select2MultipleWidget,
        )  # , number__in=prev['free']
        self.fields["presented"] = forms.ModelChoiceField(
            queryset=Problem.objects.filter(tournament=stage.fight.round.tournament),
            widget=Select2Widget,
            required=False,
        )  # , number__in=prev['free']
        if stage.presented:
            self.fields["presented"].initial = stage.presented_id

        self.fields["rejections"].initial = list(
            stage.rejections.all().values_list("pk", flat=True)
        )

        self.fields["rep"] = forms.ModelChoiceField(
            queryset=stage.rep_attendance.team.teammember_set(manager="students")
            .prefetch_related("attendee__active_user__user")
            .all(),
            widget=Select2Widget,
            required=False,
        )
        if stage.reporter:
            self.fields["rep"].initial = stage.rep_attendance.active_person
        self.fields["opp"] = forms.ModelChoiceField(
            queryset=stage.opp_attendance.team.teammember_set(manager="students")
            .prefetch_related("attendee__active_user__user")
            .all(),
            widget=Select2Widget,
            required=False,
        )
        if stage.opponent:
            self.fields["opp"].initial = stage.opp_attendance.active_person
        if stage.fight.round.review_phase:
            self.fields["rev"] = forms.ModelChoiceField(
                queryset=stage.rev_attendance.team.teammember_set(manager="students")
                .prefetch_related("attendee__active_user__user")
                .all(),
                widget=Select2Widget,
                required=False,
            )
            if stage.reviewer:
                self.fields["rev"].initial = stage.rev_attendance.active_person

        self.grades = []
        self.stage = stage
        index = 30
        trn: Tournament = stage.fight.round.tournament
        for js in stage.fight.jurorsession_set(manager="voting").all():
            j = {"name": js.juror.attendee.full_name, "pk": js.pk}

            f = forms.IntegerField(
                min_value=1, max_value=10, required=False, disabled=stage.jurors_grading
            )
            self.fields["grade-%d-rep" % (js.pk,)] = f
            f.widget.attrs["tabindex"] = index
            f.jurorsession = js
            f.attendance = stage.rep_attendance
            try:
                f.initial_obj = stage.rep_attendance.jurorgrade_set.get(
                    juror_session=js
                )
                if stage.jurors_grading and not trn.fa_show_grades:
                    f.graded = True
                else:
                    f.initial = int(f.initial_obj.grade)
            except:
                pass

            f = forms.IntegerField(
                min_value=1, max_value=10, required=False, disabled=stage.jurors_grading
            )
            self.fields["grade-%d-opp" % (js.pk,)] = f
            f.widget.attrs["tabindex"] = index + 50
            f.jurorsession = js
            f.attendance = stage.opp_attendance
            try:
                f.initial_obj = stage.opp_attendance.jurorgrade_set.get(
                    juror_session=js
                )
                if stage.jurors_grading and not trn.fa_show_grades:
                    f.graded = True
                else:
                    f.initial = int(f.initial_obj.grade)
            except:
                pass

            if stage.fight.round.review_phase:
                f = forms.IntegerField(
                    min_value=1,
                    max_value=10,
                    required=False,
                    disabled=stage.jurors_grading,
                )
                self.fields["grade-%d-rev" % (js.pk,)] = f
                f.widget.attrs["tabindex"] = index + 100
                f.jurorsession = js
                f.attendance = stage.rev_attendance
                try:
                    f.initial_obj = stage.rev_attendance.jurorgrade_set.get(
                        juror_session=js
                    )
                    if stage.jurors_grading and not trn.fa_show_grades:
                        f.graded = True
                    else:
                        f.initial = int(f.initial_obj.grade)
                except:
                    pass

            index += 1
            self.grades.append(j)

    def as_grades_table(self):

        def graded(f):
            if hasattr(f, "graded"):
                return "graded"
            return ""

        if self.stage.fight.round.review_phase:
            return format_html_join(
                "",
                "<tr><td>{}</td><td>{} {}</td><td>{} {}</td><td>{} {}</td></tr>",
                (
                    (
                        j["name"],
                        self.__getitem__("grade-%d-rep" % (j["pk"])),
                        graded(self.fields["grade-%d-rep" % (j["pk"])]),
                        self.__getitem__("grade-%d-opp" % (j["pk"])),
                        graded(self.fields["grade-%d-opp" % (j["pk"])]),
                        self.__getitem__("grade-%d-rev" % (j["pk"])),
                        graded(self.fields["grade-%d-rev" % (j["pk"])]),
                    )
                    for j in self.grades
                ),
            )
        else:
            return format_html_join(
                "",
                "<tr><td>{}</td><td>{} {}</td><td>{} {}</td></tr>",
                (
                    (
                        j["name"],
                        self.__getitem__("grade-%d-rep" % (j["pk"])),
                        graded(self.fields["grade-%d-rep" % (j["pk"])]),
                        self.__getitem__("grade-%d-opp" % (j["pk"])),
                        graded(self.fields["grade-%d-opp" % (j["pk"])]),
                    )
                    for j in self.grades
                ),
            )


class ManageForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super(ManageForm, self).__init__(*args, **kwargs)

        self.rs = []
        for round in tournament.round_set.all():
            r = []
            self.fields["import-%d" % round.order] = forms.ModelChoiceField(
                queryset=tournament.round_set(manager="selectives").all(),
                required=False,
            )
            for fight in round.fight_set.select_related("room").all():
                f = forms.BooleanField(label=fight.room.name, required=False)
                f.initial = fight.locked
                ass = forms.ModelMultipleChoiceField(
                    queryset=tournament.attendee_set(manager="assistants"),
                    widget=Select2MultipleWidget,
                    required=False,
                )
                ass.fight = fight
                f.fight = fight
                ass.old_attendees = None
                if fight.operators.count() > 0:
                    ass.initial = fight.operators.all().values_list("id", flat=True)
                    ass.old_attendees = ", ".join(
                        [a.full_name for a in fight.operators.all()]
                    )
                r.append("%d-%d" % (round.order, fight.pk))
                self.fields["locked-%d-%d" % (round.order, fight.pk)] = f
                self.fields["op-%d-%d" % (round.order, fight.pk)] = ass
            self.rs.append((round.order, r))

    def rounds(self):
        for order, round in self.rs:
            fights = []
            for name in round:
                locked = self.__getitem__("locked-%s" % (name,))
                fi = {
                    "locked": locked,
                    "operators": self.__getitem__("op-%s" % (name,)),
                }
                fi["stages"] = self.fields["locked-%s" % name].fight.stage_set.all()
                fights.append(fi)
            yield {
                "fights": fights,
                "import": self.__getitem__("import-%s" % (order,)),
            }


class SlidesRedirForm(forms.Form):
    def __init__(self, tournament, *args, **kwargs):
        super(SlidesRedirForm, self).__init__(*args, **kwargs)

        self.fields["server"] = forms.ModelChoiceField(
            queryset=tournament.fileserver_set.all(), widget=Select2Widget
        )

        self.fields["round"] = forms.ModelChoiceField(
            queryset=tournament.round_set.all(), widget=Select2Widget
        )

        self.fields["path"] = forms.CharField(
            label="path from login dir without leading /"
        )


class SlidesForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super(SlidesForm, self).__init__(*args, **kwargs)

        self.rs = []
        self.slides = {}
        for round in tournament.round_set.filter():
            r = []
            for fight in round.fight_set.select_related("room").all():
                s = []
                for stage in fight.stage_set.all():
                    field = forms.FileField(
                        label=f"{round.order}{fight.room.name} {stage.rep_attendance.team.origin.name}",
                        widget=ClearableFileInput(),
                        validators=[pdf_validator],
                        required=False,
                    )
                    field.stage = stage
                    field.initial = stage.pdf_presentation
                    self.fields[
                        "slides-%d-%d-%d" % (round.order, fight.pk, stage.order)
                    ] = field
                    s.append("%d-%d-%d" % (round.order, fight.pk, stage.order))
                r.append({"stages": s, "room": fight.room.name})
            self.rs.append(r)

    def rounds(self):
        for order, round in enumerate(self.rs):
            yield [
                [
                    {
                        "room": name["room"],
                        "slides_file": self.__getitem__("slides-%s" % (st,)),
                        # "fight_id": self.fight_id[st],
                    }
                    for st in name["stages"]
                ]
                for name in round
            ]


class PublishForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super(PublishForm, self).__init__(*args, **kwargs)

        self.rs = []
        self.valid = {}
        self.pdf_preview = {}
        self.pdf_result = {}
        self.pdf_rank = {}
        self.fight_id = {}

        partial_tag = PdfTag.objects.filter(
            tournament=tournament, name="Partials"
        ).first()

        for round in tournament.round_set.filter():
            rank = forms.BooleanField(required=False)
            rank.initial = round.publish_ranking
            rank.round = round
            self.fields["rank-%d" % round.order] = rank

            sched = forms.BooleanField(required=False)
            sched.initial = round.publish_schedule
            sched.round = round
            self.fields["sched-%d" % round.order] = sched

            fixed = forms.BooleanField(required=False)
            fixed.initial = round.preview_fixed_problem
            fixed.round = round
            self.fields["fixed-%d" % round.order] = fixed

            jury = forms.BooleanField(required=False)
            jury.initial = round.publish_jurors
            jury.round = round
            self.fields["jury-%d" % round.order] = jury

            active = forms.BooleanField(required=False)
            active.initial = round.currently_active
            active.round = round
            self.fields["active-%d" % round.order] = active

            fblocked = forms.BooleanField(required=False)
            fblocked.initial = round.feedback_locked
            fblocked.round = round
            self.fields["fblocked-%d" % round.order] = fblocked

            review = forms.BooleanField(required=False)
            review.initial = round.review_phase
            review.round = round
            self.fields["review-%d" % round.order] = review

            r = []
            for fight in round.fight_set.select_related("room").all():
                fg = forms.BooleanField(label=fight.room.name, required=False)
                fg.initial = fight.publish_grades
                fg.fight = fight

                fp = forms.BooleanField(label=fight.room.name, required=False)
                fp.initial = fight.publish_preview
                fp.fight = fight

                fpsingle = forms.BooleanField(label=fight.room.name, required=False)
                fpsingle.initial = fight.publish_partials
                fpsingle.fight = fight

                fpslides = forms.BooleanField(label=fight.room.name, required=False)
                fpslides.initial = fight.publish_slides
                fpslides.fight = fight

                fppart = forms.ModelChoiceField(
                    Pdf.objects.filter(tournament=tournament, tags__in=[partial_tag]),
                    widget=Select2Widget,
                    required=False,
                )
                fppart.initial = fight.pdf_partial_grades
                fppart.fight = fight

                r.append("%d-%d" % (round.order, fight.pk))
                self.fields["grades-%d-%d" % (round.order, fight.pk)] = fg
                self.fields["preview-%d-%d" % (round.order, fight.pk)] = fp
                self.fields["partial-%d-%d" % (round.order, fight.pk)] = fppart
                self.fields["slides-%d-%d" % (round.order, fight.pk)] = fpslides
                self.fields["single-%d-%d" % (round.order, fight.pk)] = fpsingle

                self.valid["%d-%d" % (round.order, fight.pk)] = fight_grades_valid(
                    fight
                )
                self.pdf_preview["%d-%d" % (round.order, fight.pk)] = (
                    fight.pdf_preview_id
                )
                self.pdf_result["%d-%d" % (round.order, fight.pk)] = fight.pdf_result_id
                self.pdf_rank["%d-%d" % (round.order, fight.pk)] = round.pdf_ranking
                self.fight_id["%d-%d" % (round.order, fight.pk)] = fight.pk

            self.rs.append(r)

        self.fields["slides_public"] = forms.BooleanField(
            initial=tournament.slides_public, required=False
        )
        self.fields["protection"] = forms.ChoiceField(
            choices=Tournament.RESULTS_ACCESS_TYPE, initial=tournament.results_access
        )
        self.fields["password"] = forms.CharField(
            widget=forms.PasswordInput, required=False
        )

    def rounds(self):
        for order, round in enumerate(self.rs):
            yield [
                {
                    "grade_check": self.__getitem__("grades-%s" % (name,)),
                    "preview_check": self.__getitem__("preview-%s" % (name,)),
                    "single_publish": self.__getitem__("single-%s" % (name,)),
                    "slides_publish": self.__getitem__("slides-%s" % (name,)),
                    "rank_check": self.__getitem__("rank-%d" % (order + 1,)),
                    "sched_check": self.__getitem__("sched-%d" % (order + 1,)),
                    "jury_check": self.__getitem__("jury-%d" % (order + 1,)),
                    "active_check": self.__getitem__("active-%d" % (order + 1,)),
                    "review_check": self.__getitem__("review-%d" % (order + 1,)),
                    "fixed_check": self.__getitem__("fixed-%d" % (order + 1,)),
                    "fblocked_check": self.__getitem__("fblocked-%d" % (order + 1,)),
                    "partial_file": self.__getitem__("partial-%s" % (name,)),
                    "valid": self.valid[name],
                    "pdf_preview": self.pdf_preview[name],
                    "pdf_result": self.pdf_result[name],
                    "pdf_rank": self.pdf_rank[name],
                    "fight_id": self.fight_id[name],
                }
                for name in round
            ]

    def clean(self):
        cleaned_data = super(PublishForm, self).clean()

        rp = []
        for order, round in enumerate(self.rs):
            pubed = cleaned_data.get("rank-%d" % (order + 1))
            if pubed and not all(rp):
                raise forms.ValidationError(
                    "You have to publish rankings consecutively."
                )
            rp.append(pubed)

        sp = []
        for order, round in enumerate(self.rs):
            pubed = cleaned_data.get("sched-%d" % (order + 1))
            if pubed and not all(sp):
                raise forms.ValidationError(
                    "You have to publish schedule rounds consecutively."
                )
            sp.append(pubed)


class ScanForm(forms.Form):

    pdf = forms.ModelChoiceField(Pdf.objects.none())

    page = forms.IntegerField(required=False)
    jurorsession = forms.ModelChoiceField(
        JurorSession.objects.none(), required=False, widget=Select2Widget
    )
    stage = forms.IntegerField(min_value=1, max_value=4, required=False)
    orientation = forms.ChoiceField(
        choices=(
            (None, "level"),
            (Image.ROTATE_90, "90 ccw"),
            (Image.ROTATE_270, "90 cw"),
            (Image.ROTATE_180, "180 turn"),
        ),
        required=False,
        label="Rotation to achieve correct one",
    )

    def __init__(self, tournament, *args, **kwargs):
        super(ScanForm, self).__init__(*args, **kwargs)
        self.fields["pdf"].queryset = tournament.pdf_set.all()
        self.fields["jurorsession"].queryset = JurorSession.objects.filter(
            juror__attendee__tournament=tournament
        )


class SlidesImportForm(forms.Form):

    def __init__(self, sftp: SFTPClient, trn: Tournament, round, path, *args, **kwargs):
        super(SlidesImportForm, self).__init__(*args, **kwargs)

        def sizeof_fmt(num, suffix="B"):
            for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
                if abs(num) < 1024.0:
                    return f"{num:3.1f}{unit}{suffix}"
                num /= 1024.0
            return f"{num:.1f}Yi{suffix}"

        sftp.chdir(path)

        def list_dir(cli, prefix=""):
            files = []

            for file in sftp.listdir_attr():
                if file.filename.startswith("."):
                    continue
                if file.filename == "System Volume Information":
                    continue
                if S_ISDIR(file.st_mode):
                    print(file.filename + " is folder")
                    sftp.chdir(file.filename)
                    files += list_dir(sftp, os.path.join(prefix, file.filename))
                    sftp.chdir("..")
                elif file.filename.lower().endswith(".pdf"):
                    files.append(
                        (
                            os.path.join(prefix, file.filename),
                            RemoteFile(
                                name=os.path.join(prefix, file.filename),
                                size=sizeof_fmt(file.st_size),
                                mtime=datetime.fromtimestamp(file.st_mtime),
                                imported=False,  # file.filename in imported,
                            ),
                        )
                    )
            return files

        files = list_dir(sftp)

        files = sorted(files, key=lambda x: x[1].name, reverse=True)

        for file in files:
            base = os.path.split(file[1].name)[0]
            try:
                ori = Origin.objects.filter(slug=base, tournament=trn).first()
                file[1].origin = ori
            except Origin.DoesNotExist:
                pass

        self.fields["files"] = forms.MultipleChoiceField(choices=files, required=False)
