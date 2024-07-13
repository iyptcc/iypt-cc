from django.db.models import Q

from apps.account.models import ParticipationRole

from .models import Application, AttendeeProperty, UserPropertyValue
from .utils import persons_data


class Validator:

    depends_on = []
    require = []

    def validate(self, nodes, *args, **kwargs):
        raise NotImplementedError("This method must be subclassed")

    def passed(self, *args, **kwargs):
        nodes = {}
        for v in self.depends_on:
            nodes.update(v().passed(*args, **kwargs))
        nodes.update(self.validate(nodes, *args, **kwargs))

        return nodes


class NameValidator(Validator):

    tag = "name"

    def validate(self, nodes, *args, **kwargs):
        if "activeuser" in kwargs:
            if (
                kwargs["activeuser"].user.first_name != ""
                and kwargs["activeuser"].user.last_name != ""
            ):
                return {self.tag: "finished"}
            return {self.tag: "available"}
        else:
            raise AttributeError("NameValidator requires activeuser parameter")


class ProfileValidator(Validator):

    depends_on = [NameValidator]

    tag = "profile"

    def validate(self, nodes, *args, **kwargs):
        if "activeuser" in kwargs and "tournament" in kwargs:
            trn = kwargs["tournament"]
            for ap in AttendeeProperty.user_objects.filter(Q(tournament=trn)):
                if not (
                    ap.apply_required.filter(type=ParticipationRole.STUDENT).exists()
                    and ap.apply_required.filter(type=ParticipationRole.JUROR).exists()
                ):
                    continue
                t = ap.user_property.type
                up = ap.user_property

                valueo = UserPropertyValue.objects.filter(
                    user=kwargs["activeuser"], property=up
                ).last()

                if valueo:
                    value = getattr(valueo, valueo.field_name[t])
                    if value == None or value == "":
                        return {self.tag: "available"}
            return {self.tag: "finished"}
        else:
            raise AttributeError(
                "ProfileValidator requires activeuser and tournament parameter"
            )


class IOCValidator(Validator):

    depends_on = [ProfileValidator]

    tag = "apply_ioc"

    def validate(self, nodes, *args, **kwargs):
        if nodes[ProfileValidator.tag] == "finished":
            try:
                if (
                    kwargs["activeuser"]
                    .attendee_set.get(tournament=kwargs["tournament"])
                    .roles.filter(type=ParticipationRole.TEAM_MANAGER)
                ):
                    return {self.tag: "finished"}
            except:
                pass
            return {self.tag: "available"}
        return {self.tag: "disabled"}


class TeamManagerValidator(Validator):

    depends_on = [ProfileValidator]

    tag = "apply_manager"

    def validate(self, nodes, *args, **kwargs):
        if nodes[ProfileValidator.tag] == "finished":
            try:
                if (
                    kwargs["activeuser"]
                    .attendee_set.get(tournament=kwargs["tournament"])
                    .roles.filter(type=ParticipationRole.TEAM_MANAGER)
                ):
                    return {self.tag: "finished"}
            except:
                pass
            return {self.tag: "available"}
        return {self.tag: "disabled"}


class ApplicationWaitValidator(Validator):

    depends_on = []

    tag = ""

    def get_roletype(self):
        raise NotImplementedError("you need to supply a Role Type")

    def validate(self, nodes, *args, **kwargs):
        if Application.objects.filter(
            applicant=kwargs["activeuser"],
            tournament=kwargs["tournament"],
            participation_role__type=self.get_roletype(),
        ).exists():
            return {self.tag: "wait"}
        return {}


class PossibleJurorValidator(Validator):

    depends_on = [ProfileValidator]

    tag = "apply_possiblejuror"

    def validate(self, nodes, *args, **kwargs):
        if nodes[ProfileValidator.tag] == "finished":
            try:
                if (
                    kwargs["activeuser"]
                    .possiblejuror_set.filter(tournament=kwargs["tournament"])
                    .exists()
                ):
                    return {self.tag: "finished"}
            except:
                pass
            return {self.tag: "available"}
        return {self.tag: "disabled"}


class PossibleJurorWaitValidator(Validator):

    depends_on = [PossibleJurorValidator]

    tag = "wait_possiblejuror"

    def validate(self, nodes, *args, **kwargs):
        try:
            pj = kwargs["activeuser"].possiblejuror_set.get(
                tournament=kwargs["tournament"]
            )
            if not pj.approved_by:
                return {self.tag: "wait"}
        except:
            pass
        return {}


class TeamManagerWaitValidator(ApplicationWaitValidator):
    depends_on = [TeamManagerValidator]
    tag = "wait_manager"

    def get_roletype(self):
        return ParticipationRole.TEAM_MANAGER


class IOCWaitValidator(ApplicationWaitValidator):
    depends_on = [IOCValidator]
    tag = "wait_ioc"

    def get_roletype(self):
        return ParticipationRole.TEAM_MANAGER


class ExperiencedJurorWaitValidator(ApplicationWaitValidator):
    depends_on = [PossibleJurorWaitValidator]
    tag = "wait_experiencedjuror"

    def get_roletype(self):
        return ParticipationRole.JUROR


class TeamRoleValidator(Validator):
    depends_on = [ProfileValidator]

    tag = []

    def get_roletype(self):
        raise NotImplementedError("you need to supply a Role Type")

    def validate(self, nodes, *args, **kwargs):
        if nodes[ProfileValidator.tag] == "finished":
            try:
                if (
                    kwargs["activeuser"]
                    .attendee_set.get(tournament=kwargs["tournament"])
                    .roles.filter(type=self.get_roletype())
                    .exists()
                ):
                    return {self.tag: "finished"}
            except:
                pass
            return {self.tag: "available"}
        return {self.tag: "disabled"}


class TeamMemberValidator(TeamRoleValidator):
    tag = "apply_teammember"

    def get_roletype(self):
        return ParticipationRole.STUDENT


class TeamLeaderValidator(TeamRoleValidator):

    tag = "apply_teamleader"

    def get_roletype(self):
        return ParticipationRole.TEAM_LEADER


class TeamVisitorValidator(TeamRoleValidator):

    tag = "associate_visitor"

    def get_roletype(self):
        return ParticipationRole.VISITOR


class TeamPasswordValidator(TeamRoleValidator):

    tag = "setpw"

    def get_roletype(self):
        return ParticipationRole.TEAM_MANAGER

    def validate(self, nodes, *args, **kwargs):
        val = super().validate(nodes, args, kwargs)
        if val[self.tag] == "finished":
            val[self.tag] = "available"
        elif val[self.tag] == "available":
            val[self.tag] = "disabled"
        return val


class VisitorWaitValidator(ApplicationWaitValidator):
    depends_on = [TeamVisitorValidator]
    tag = "wait_visitor"

    def get_roletype(self):
        return ParticipationRole.VISITOR


class TeamMemberWaitValidator(ApplicationWaitValidator):
    depends_on = [TeamMemberValidator]
    tag = "wait_teammember"

    def get_roletype(self):
        return ParticipationRole.STUDENT


class ExperiencedJurorValidator(Validator):

    depends_on = [ProfileValidator, PossibleJurorWaitValidator]

    tag = "apply_experiencedjuror"

    def validate(self, nodes, *args, **kwargs):
        try:
            if (
                kwargs["activeuser"]
                .attendee_set.get(tournament=kwargs["tournament"])
                .roles.filter(type=ParticipationRole.JUROR)
                .exists()
            ):
                return {self.tag: "finished"}
        except:
            pass
        if Application.objects.filter(
            applicant=kwargs["activeuser"],
            tournament=kwargs["tournament"],
            participation_role__type=ParticipationRole.JUROR,
        ).exists():
            return {self.tag: "finished"}
        try:
            pj = kwargs["activeuser"].possiblejuror_set.get(
                tournament=kwargs["tournament"]
            )
            if pj.approved_by:
                return {self.tag: "available"}
        except:
            pass
        return {self.tag: "disabled"}


class SetActiveValidator(Validator):

    depends_on = [
        TeamMemberWaitValidator,
        TeamManagerWaitValidator,
        VisitorWaitValidator,
        ExperiencedJurorWaitValidator,
        IOCWaitValidator,
    ]

    tags = [
        "active_experiencedjuror",
        "active_ioc",
        "active_loc",
        "active_manager",
        "active_role",
        "active_teamleader",
        "active_teamleaderjuror",
        "active_teammember",
        "active_visitor",
    ]

    def validate(self, nodes, *args, **kwargs):
        if kwargs["activeuser"].tournament == kwargs["tournament"]:
            return {t: "finished" for t in self.tags}
        elif (
            kwargs["activeuser"]
            .attendee_set.filter(tournament=kwargs["tournament"])
            .exists()
        ):
            return {t: "available" for t in self.tags}
        return {t: "disabled" for t in self.tags}


class AssociateValidator(Validator):
    tags = ["associate_role", "associate_experiencedjuror"]

    depends_on = [SetActiveValidator]

    def validate(self, nodes, *args, **kwargs):
        if nodes[SetActiveValidator.tags[0]] == "finished":
            try:
                if (
                    kwargs["activeuser"]
                    .attendee_set.get(tournament=kwargs["tournament"])
                    .teammember_set.count()
                    > 0
                ):
                    return {t: "finished" for t in self.tags}
                else:
                    return {t: "available" for t in self.tags}
            except:
                return {t: "disabled" for t in self.tags}
        return {t: "disabled" for t in self.tags}


class DataValidator(Validator):

    depends_on = [SetActiveValidator, TeamPasswordValidator, AssociateValidator]

    tag = "data"

    def validate(self, nodes, *args, **kwargs):

        if (
            kwargs["activeuser"]
            .attendee_set.filter(tournament=kwargs["tournament"])
            .exists()
        ):

            atts = kwargs["activeuser"].attendee_set.filter(
                tournament=kwargs["tournament"]
            )
            pdata, opts = persons_data(
                kwargs["activeuser"].attendee_set.filter(
                    tournament=kwargs["tournament"]
                )
            )

            for v in pdata[atts.first().id]["data"]:
                if "list" not in v:
                    v["list"] = []
            reqir = len(
                [
                    x
                    for x in pdata[atts.first().id]["data"]
                    if x["value"] in [None, ""]
                    and len(x["list"]) == 0
                    and ("image" not in x)
                    and ("file" not in x)
                    and x["required"]
                ]
            )
            print("missing")
            print(
                [
                    x
                    for x in pdata[atts.first().id]["data"]
                    if x["value"] in [None, ""]
                    and len(x["list"]) == 0
                    and ("image" not in x)
                    and ("file" not in x)
                    and x["required"]
                ]
            )
            if reqir > 0:
                return {self.tag: "available"}
            else:
                return {self.tag: "finished"}
        else:
            return {self.tag: "disabled"}
