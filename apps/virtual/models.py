from django.db import models
from django.utils import timezone
from ordered_model.models import OrderedModel

from apps.account.models import Attendee, ParticipationRole
from apps.tournament.models import Tournament


class BBBInstance(models.Model):
    name = models.CharField(max_length=128, verbose_name="Name")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    api_url = models.URLField(max_length=256, verbose_name="API URL")
    secret = models.CharField(max_length=64, verbose_name="Secret")

    def __str__(self):
        return self.name


class BBBGuest(models.Model):
    name = models.CharField(max_length=1000)
    userid = models.CharField(max_length=100)


class Hall(OrderedModel):
    GUEST_ACCEPT = "ALWAYS_ACCEPT"
    GUEST_DENY = "ALWAYS_DENY"
    GUEST_ASK = "ASK_MODERATOR"
    GUEST_POLICIES = [
        (GUEST_ACCEPT, "allow guests"),
        (GUEST_DENY, "deny guests"),
        (GUEST_ASK, "ask moderator to allow guests"),
    ]

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, verbose_name="Name")
    instance = models.ForeignKey(
        BBBInstance,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="meetings",
    )

    # mute
    mute_on_start = models.BooleanField(default=False, verbose_name="mute on join")

    # settings for disabling features
    lock_settings_disable_cam = models.BooleanField(
        default=False, verbose_name="disable video sharing"
    )
    lock_settings_disable_private_chat = models.BooleanField(
        default=False, verbose_name="disable private chat"
    )
    lock_settings_disable_note = models.BooleanField(
        default=False, verbose_name="disable notes"
    )

    record = models.BooleanField(default=False)

    # attendees and guests
    allow_attendees_to_start_meeting = models.BooleanField(
        default=False, verbose_name="attendees can start meeting"
    )
    guest_policy = models.CharField(
        max_length=16, choices=GUEST_POLICIES, default=GUEST_DENY, verbose_name="guests"
    )

    roles = models.ManyToManyField(ParticipationRole, through="HallRole", blank=True)
    description = models.TextField(null=True, blank=True)

    order_with_respect_to = "tournament"

    virtual_attendees = models.ManyToManyField(Attendee, blank=True)
    virtual_guests = models.ManyToManyField(BBBGuest, blank=True)

    def __str__(self):
        return "%s" % (self.name,)


class HallRole(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    role = models.ForeignKey(ParticipationRole, on_delete=models.CASCADE)
    mode = models.CharField(max_length=40, choices=Tournament.BBB_ROLES)

    class Meta:
        unique_together = ("hall", "role")


class Stream(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, verbose_name="Name")
    access = models.ManyToManyField(ParticipationRole, blank=True)

    stream_name = models.CharField(max_length=200, null=True, blank=True)
    hls_format = models.CharField(max_length=1024, null=True, blank=True)
    mpd_format = models.CharField(max_length=1024, null=True, blank=True)
    external_link = models.CharField(max_length=1024, null=True, blank=True)

    @property
    def random_urls(self):
        edge = self.streamedgeserver_set.order_by("?").first()
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        return {
            "hls": self.hls_format.format_map(
                {
                    "subdomain": edge.url,
                    "streamname": self.stream_name,
                    "timestamp": timestamp,
                }
            ),
            "mpd": self.mpd_format.format_map(
                {
                    "subdomain": edge.url,
                    "streamname": self.stream_name,
                    "timestamp": timestamp,
                }
            ),
        }


class StreamEdgeServer(models.Model):
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE)
    url = models.CharField(max_length=1024)
