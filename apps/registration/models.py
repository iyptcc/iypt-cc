from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django_countries.fields import CountryField
from ordered_model.models import OrderedModel

from apps.account.models import ActiveUser, Attendee, ParticipationRole
from apps.team.models import Team, TeamRole
from apps.tournament.models import Origin, Tournament

# Create your models here.

class Application(models.Model):

    applicant = models.ForeignKey(ActiveUser, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    participation_role = models.ForeignKey(ParticipationRole, on_delete=models.CASCADE)

    origin = models.ForeignKey(Origin, blank=True, null=True, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, blank=True, null=True, on_delete=models.CASCADE)
    team_role = models.ForeignKey(TeamRole, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        permissions = (
            ("manage_team", "Manage the Team where user is TL"),
            ("manage_data", "Set users participation data"),
            ("accept_team", "Accept new Teams"),
            ("accept_role", "Accept new Persons for Role"),
            ("accept_juror", "Accept new Jurors"),
            ("manage_all_teams", "Manage all Teams"),
            ("view_all_data", "View all Attendee Data"),
        )

    def __str__(self):
        return "%s for %s"%(self.applicant, self.tournament)

class Property(OrderedModel):
    INT = "int"
    STRING = "string"
    DATETIME = "datetime"
    DATE = "date"
    IMAGE = "image"
    PDF = "pdf"
    TEXT = "text"
    GENDER = "gender"
    BOOLEAN = "boolean"
    BOOLEAN_TRUE = "boolean_true"
    PREFERRED_NAME = "preferred_name"
    PREFERRED_NAME_SHORT = "preferred_name_short"
    CHOICE = "choice"
    MULTIPLE_CHOICE = "multiple_choice"
    CONFLICT_ORIGINS = "conflict_origins"
    COUNTRY = "country"
    PROBLEM = "problem"
    TYPE_CHOICES = (
        (INT, 'Integer'),
        (STRING, 'String'),
        (DATETIME, 'datetime'),
        (DATE, 'date'),
        (IMAGE, 'image'),
        (PDF, 'pdf'),
        (TEXT, 'text'),
        (GENDER, 'gender'),
        (BOOLEAN, 'boolean'),
        (BOOLEAN_TRUE, 'required true boolean'),
        (PREFERRED_NAME, 'preferred name'),
        (PREFERRED_NAME_SHORT, 'preferred name short'),
        (CHOICE, 'Select One'),
        (MULTIPLE_CHOICE, 'Select Multiple'),
        (CONFLICT_ORIGINS, 'Conflict with Origins'),
        (COUNTRY, 'Country (ISO)'),
        (PROBLEM, 'Problem'),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(choices=TYPE_CHOICES, max_length=30)

    def __str__(self):
        return "%s (%s)"%(self.name, self.type)


class PropertyChoice(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)

    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class UserProperty(Property):

    TYPE_CHOICES = (
        (Property.INT, 'Integer'),
        (Property.STRING, 'String'),
        (Property.DATETIME, 'datetime'),
        (Property.DATE, 'date'),
        (Property.IMAGE, 'image'),
        (Property.PDF, 'pdf'),
        (Property.TEXT, 'text'),
        (Property.GENDER, 'gender'),
        (Property.BOOLEAN, 'boolean'),
        (Property.BOOLEAN_TRUE, 'required true boolean'),
        (Property.PREFERRED_NAME, 'preferred name'),
        (Property.PREFERRED_NAME_SHORT, 'preferred name short'),
        (Property.CHOICE, 'Select One'),
        (Property.MULTIPLE_CHOICE, 'Select Multiple'),
        (Property.COUNTRY, 'Country (ISO)'),
    )

    def __str__(self):
        return "%s (%s)"%(self.name, self.type)

class PropertyValue(models.Model):

    creation = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(ActiveUser, on_delete=models.CASCADE)

    int_value = models.IntegerField(blank=True, null=True)
    string_value = models.CharField(max_length=255, blank=True, null=True)
    datetime_value = models.DateTimeField(blank=True, null=True)
    date_value = models.DateField(blank=True, null=True)
    image_value = models.ImageField(blank=True, null=True)
    file_value = models.FileField(blank=True, null=True)
    text_value = models.TextField(blank=True, null=True)
    bool_value = models.NullBooleanField(blank=True, null=True)
    country_value = CountryField(blank=True, null=True)

    field_name = {}
    field_name[UserProperty.INT] = "int_value"
    field_name[UserProperty.STRING] = "string_value"
    field_name[UserProperty.DATETIME] = "datetime_value"
    field_name[UserProperty.DATE] = "date_value"
    field_name[UserProperty.IMAGE] = "image_value"
    field_name[UserProperty.PDF] = "file_value"
    field_name[UserProperty.TEXT] = "text_value"
    field_name[UserProperty.GENDER] = "string_value"
    field_name[UserProperty.BOOLEAN] = "bool_value"
    field_name[UserProperty.BOOLEAN_TRUE] = "bool_value"
    field_name[UserProperty.PREFERRED_NAME] = "string_value"
    field_name[UserProperty.PREFERRED_NAME_SHORT] = "string_value"
    field_name[UserProperty.COUNTRY] = "country_value"
    field_name[UserProperty.PROBLEM] = "int_value"


    choices_value = models.ManyToManyField(PropertyChoice, blank=True)
    conflict_origins = models.ManyToManyField(Origin, blank=True)

    def toString(self):
        s = None
        if self.int_value:
            s = self.int_value
        elif self.string_value:
            s = self.string_value
        elif self.datetime_value:
            s = self.datetime_value
        elif self.date_value:
            s = self.date_value
        elif self.text_value:
            s = self.text_value
        elif self.bool_value != None:
            s = self.bool_value
        elif self.country_value:
            s = self.country_value
        elif self.image_value:
            s = self.image_value.name
        elif self.file_value:
            s = self.file_value.name
        elif self.choices_value.count() > 0:
            s = ", ".join(self.choices_value.all().values_list("name",flat=True))
        elif self.conflict_origins.count() > 0:
            s = ", ".join(self.conflict_origins.all().values_list("name",flat=True))
        else:
            return None
        return "%s"%s

    def __str__(self):
        s = self.toString()
        return "%s edit %s@%s"%(s, self.author, self.creation)

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.image_value:
                fname = self.image_value.name.replace('/', '-')
                if hasattr(self,"property"):
                    if self.property != None:
                        self.image_value.name = 'properties'+'/'+ "%d-%s"%(self.property.id, slugify(self.property.name))+ '/' + fname
                else:
                    self.image_value.name = 'properties'+'/'+ "unknown" + '/' + fname
            if self.file_value:
                fname = self.file_value.name.replace('/', '-')
                if hasattr(self,"property"):
                    if self.property != None:
                        self.file_value.name = 'properties'+'/'+ "%d-%s"%(self.property.id, slugify(self.property.name))+ '/' + fname
                else:
                    self.file_value.name = 'properties'+'/'+ "unknown" + '/' + fname
        super().save(*args, **kwargs)

class UserPropertyValue(PropertyValue):

    property = models.ForeignKey(UserProperty, on_delete=models.CASCADE)
    user = models.ForeignKey(ActiveUser, on_delete=models.CASCADE)

    def __str__(self):
        return "%s for %s = %s"%(self.property, self.user, super().__str__())

class DefaultAttendeePropertyManager(models.Manager):
    def get_queryset(self):
        return super(DefaultAttendeePropertyManager, self).get_queryset().filter(hidden=False)

class AttendeeProperty(Property):

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    required = models.ManyToManyField(ParticipationRole, related_name="required_properties", blank=True)
    optional = models.ManyToManyField(ParticipationRole, related_name="optional_properties", blank=True)

    edit_deadline = models.DateTimeField(blank=True, null=True)

    user_property = models.ForeignKey(UserProperty, null=True, blank=True, on_delete=models.CASCADE)

    data_utilisation = models.TextField(verbose_name="Explanation why this data is acquired", blank=True, null=True)

    hidden = models.BooleanField(default=False)

    required_if = models.ForeignKey("registration.AttendeeProperty", blank=True, null=True, on_delete=models.CASCADE)

    manager_confirmed = models.BooleanField(default=False)

    apply_required = models.ManyToManyField(ParticipationRole, related_name="apply_properties", blank=True)

    objects = models.Manager()

    user_objects = DefaultAttendeePropertyManager()

    order_with_respect_to = "tournament"

    def __str__(self):
        return "%s in %s (%s)"%(self.name, self.tournament, self.get_type_display())


class DefaultAttendeePropertyValueManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(confirmed=True)

class AttendeePropertyValue(PropertyValue):

    property = models.ForeignKey(AttendeeProperty, on_delete=models.CASCADE)
    attendee = models.ForeignKey(Attendee, on_delete=models.CASCADE)

    confirmed = models.BooleanField(default=True)

    objects = DefaultAttendeePropertyValueManager()

    unconfirmed = models.Manager()

    def __str__(self):
        uc = ""
        if not self.confirmed:
            uc=" unconfirmed"
        return "%s for %s = %s%s"%(self.property, self.attendee, super().__str__(),uc)
