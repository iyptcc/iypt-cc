from django.contrib.auth.models import Group, User
from django.db import IntegrityError, models

from apps.tournament.models import Tournament


class ParticipationRole(models.Model):
    FIGHT_ASSISTANT = 'fa'
    STUDENT = 'st'
    TEAM_LEADER = 'tl'
    JUROR = 'ju'
    VISITOR = 'vi'
    EC = 'ec'
    TEAM_MANAGER = 'tm'
    LOC = 'lc'
    IOC = 'ic'
    ROLE_TYPE = (
        (FIGHT_ASSISTANT, 'Fight Assistant'),
        (STUDENT, 'Student'),
        (TEAM_LEADER, 'Team Leader'),
        (JUROR, 'Juror'),
        (VISITOR, 'Visitor'),
        (EC, 'EC Member'),
        (TEAM_MANAGER, 'Team Manager'),
        (LOC, 'Local Organising Committee'),
        (IOC, 'International Organising Committee'),
    )
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=2, choices=ROLE_TYPE, null=True, blank=True)

    groups = models.ManyToManyField(Group,blank=True)

    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    approvable_by = models.ManyToManyField("account.ParticipationRole", blank=True)

    global_limit = models.PositiveIntegerField(blank=True, null=True)

    attending = models.BooleanField(default=True)

    def __str__(self):
        return "%s"%self.name

# Create your models here.

class AssistantsManager(models.Manager):
    def get_queryset(self):
        return super(AssistantsManager, self).get_queryset().filter(roles__type=ParticipationRole.FIGHT_ASSISTANT)


class Attendee(models.Model):
    active_user = models.ForeignKey('ActiveUser', on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    groups = models.ManyToManyField(Group,blank=True)

    roles = models.ManyToManyField(ParticipationRole, blank=True)

    objects = models.Manager()

    assistants = AssistantsManager()

    SKINS =(('skin-blue', "blue" ),
            ('skin-blue-light', "blue light" ),
            ('skin-yellow', "yellow" ),
            ('skin-yellow-light', "yellow light" ),
            ('skin-green', "green" ),
            ('skin-green-light', "green light" ),
            ('skin-purple', "purple" ),
            ('skin-purple-light', "purple light" ),
            ('skin-red', "red" ),
            ('skin-red-light', "red light" ),
            ('skin-black', "black" ),
            ('skin-black-light', "black light" ),)

    ui_skin = models.CharField(max_length=50, choices=SKINS, null=True, blank=True)

    class Meta:
        unique_together = ('active_user', 'tournament',)
        permissions = (
            ("view_person", "Can list all person details"),
            ("view_all_persons", "Can list all persons"),
        )

    def __str__(self):
        return "%s"%(self.full_name ,)

    @property
    def first_name(self):
        return self.active_user.user.first_name

    @property
    def last_name(self):
        return self.active_user.user.last_name

    @property
    def full_name(self):
        return "%s %s"%(self.first_name,self.last_name)

    @property
    def abbr_name(self):
        return "%s. %s" % (self.first_name[0], self.last_name)

    @property
    def preferred_name(self):
        try:
            pn = self.attendeepropertyvalue_set.filter(property__type="preferred_name").last().string_value
            return pn
        except:
            return self.full_name

class ActiveUser(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    active = models.ForeignKey(Attendee, on_delete=models.SET_NULL, blank=True, null=True)
    tournaments = models.ManyToManyField(Tournament,through=Attendee, blank=True)
    avatar = models.ImageField(upload_to='avatars', blank=True, null=True)

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
        return self.user.username

    def save(self, *args, **kwargs):
        if self.active:
            if self.active.active_user == self:
                super(ActiveUser, self).save(*args, **kwargs)
            else:
                raise IntegrityError("active user must be one of the assigned tournaments")
                return
        else:
            super(ActiveUser, self).save(*args, **kwargs)
