import binascii
import os

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission, PermissionsMixin, User
from django.db import IntegrityError, models
from django.db.models import Q

from apps.tournament.models import Tournament


class ParticipationRole(models.Model):
    FIGHT_ASSISTANT = "fa"
    STUDENT = "st"
    TEAM_LEADER = "tl"
    JUROR = "ju"
    VISITOR = "vi"
    CHAIR = "ch"
    EC = "ec"
    TEAM_MANAGER = "tm"
    LOC = "lc"
    IOC = "ic"
    ROLE_TYPE = (
        (FIGHT_ASSISTANT, "Fight Assistant"),
        (STUDENT, "Student"),
        (TEAM_LEADER, "Team Leader"),
        (JUROR, "Juror"),
        (CHAIR, "Chair"),
        (VISITOR, "Visitor"),
        (EC, "EC Member"),
        (TEAM_MANAGER, "Team Manager"),
        (LOC, "Local Organising Committee"),
        (IOC, "International Organising Committee"),
    )

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=2, choices=ROLE_TYPE, null=True, blank=True)

    groups = models.ManyToManyField(Group, blank=True)

    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    approvable_by = models.ManyToManyField("account.ParticipationRole", blank=True)

    global_limit = models.PositiveIntegerField(blank=True, null=True)

    attending = models.BooleanField(default=True)

    require_possiblejuror = models.BooleanField(default=False)

    application_deadline = models.DateTimeField(blank=True, null=True)

    virtual_room_role = models.CharField(
        max_length=30, choices=Tournament.BBB_ROLES, null=True, blank=True
    )

    virtual_name_tag = models.CharField(max_length=50, null=True, blank=True)
    virtual_show_team = models.BooleanField(default=False)

    def __str__(self):
        return "%s" % self.name


class AssistantsManager(models.Manager):
    def get_queryset(self):
        return (
            super(AssistantsManager, self)
            .get_queryset()
            .filter(roles__type=ParticipationRole.FIGHT_ASSISTANT)
        )


class Attendee(models.Model):
    active_user = models.ForeignKey("ActiveUser", on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    groups = models.ManyToManyField(Group, blank=True)

    roles = models.ManyToManyField(ParticipationRole, blank=True)

    objects = models.Manager()

    assistants = AssistantsManager()

    SKINS = (
        ("skin-blue", "blue"),
        ("skin-blue-light", "blue light"),
        ("skin-yellow", "yellow"),
        ("skin-yellow-light", "yellow light"),
        ("skin-green", "green"),
        ("skin-green-light", "green light"),
        ("skin-purple", "purple"),
        ("skin-purple-light", "purple light"),
        ("skin-red", "red"),
        ("skin-red-light", "red light"),
        ("skin-black", "black"),
        ("skin-black-light", "black light"),
    )

    ui_skin = models.CharField(max_length=50, choices=SKINS, null=True, blank=True)

    class Meta:
        unique_together = (
            "active_user",
            "tournament",
        )
        permissions = (
            ("view_person", "Can list all person details"),
            ("view_all_persons", "Can list all persons"),
        )

    def __str__(self):
        return "%s" % (self.full_name,)

    @property
    def first_name(self):
        return self.active_user.user.first_name

    @property
    def last_name(self):
        return self.active_user.user.last_name

    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    @property
    def abbr_name(self):
        return "%s. %s" % (self.first_name[0], self.last_name)

    @property
    def preferred_name(self):
        try:
            pn = (
                self.attendeepropertyvalue_set.filter(property__type="preferred_name")
                .last()
                .string_value
            )
            return pn
        except (
            apps.get_model("registration.AttendeePropertyValue").DoesNotExist,
            AttributeError,
        ):
            return self.full_name

    def has_permission(self, perm):

        if self.active_user.user.is_superuser:
            return True

        user_groups_field = get_user_model()._meta.get_field("groups")
        user_groups_query = "group__%s" % user_groups_field.related_query_name()

        # additional check if group is active

        active_groups = self.groups.all()

        try:
            for r in self.roles.all():
                active_groups |= r.groups.all()
        except AttributeError:
            pass

        perms = Permission.objects.filter(
            Q(group__in=active_groups) | Q(**{user_groups_query: self.active_user.user})
        )

        perms = perms.values_list("content_type__app_label", "codename").order_by()
        perm_str = {"%s.%s" % (ct, name) for ct, name in perms}
        return perm in perm_str


class ActiveUser(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    active = models.ForeignKey(
        Attendee, on_delete=models.SET_NULL, blank=True, null=True
    )
    tournaments = models.ManyToManyField(Tournament, through=Attendee, blank=True)
    avatar = models.ImageField(upload_to="avatars", blank=True, null=True)

    @property
    def tournament(self):
        try:
            act = self.active
            return act.tournament
        except Attendee.DoesNotExist:
            return None
        except AttributeError:
            return None

    @property
    def groups(self):
        try:
            act = self.active
            return act.groups
        except Attendee.DoesNotExist:
            return Group.objects.none()
        except AttributeError:
            return Group.objects.none()

    def __str__(self):
        return f"{self.user.username} <{self.user.email}>"

    def save(self, *args, **kwargs):
        if self.active:
            if self.active.active_user == self:
                super(ActiveUser, self).save(*args, **kwargs)
            else:
                raise IntegrityError(
                    "active user must be one of the assigned tournaments"
                )
                return
        else:
            super(ActiveUser, self).save(*args, **kwargs)


class ApiPermissionsMixin(PermissionsMixin):

    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions "
        "granted to each of their groups.",
        related_name="apiuser_set",
        related_query_name="apiuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="apiuser_set",
        related_query_name="apiuser",
    )


class ApiUser(ApiPermissionsMixin):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    username = models.CharField(max_length=150, null=True, blank=True)

    is_active = True

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    @property
    def profile(self):
        return self


class Token(models.Model):
    """
    The cc authorization token model.
    """

    key = models.CharField("Key", max_length=128, primary_key=True)
    user = models.OneToOneField(
        ApiUser,
        related_name="auth_token",
        on_delete=models.CASCADE,
        verbose_name="User",
    )
    created = models.DateTimeField("Created", auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        return self.key
