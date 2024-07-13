from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseRedirect

from ..account.models import Attendee
from .requests import RequestFailedError, execute_api_call, get_call_url

GUEST_ACCEPT = "ALWAYS_ACCEPT"
GUEST_DENY = "ALWAYS_DENY"
GUEST_ASK = "ASK_MODERATOR"
GUEST_POLICIES = [
    (GUEST_ACCEPT, "Gäste hereinlassen"),
    (GUEST_DENY, "Gäste abweisen"),
    (GUEST_ASK, "Warteraumfreigabe durch Moderator"),
]

from apps.tournament.models import Tournament

from .models import BBBGuest, Hall


def create_hall(hall: Hall):

    signer = signing.Signer(salt="bbb-passwords")

    kwargs = {
        "meetingID": "%s-h-%d" % (hall.tournament.slug, hall.id),
        "name": hall.name,
        "attendeePW": signer.sign("ha-%d" % hall.id).replace(":", "-"),
        "moderatorPW": signer.sign("hm-%d" % hall.id).replace(":", "-"),
        "maxParticipants": 1000,
        "logoutURL": "https://cc.iypt.org",
        "muteOnStart": hall.mute_on_start,
        "allowModsToUnmuteUsers": False,
        "lockSettingsDisableCam": hall.lock_settings_disable_cam,
        "lockSettingsDisablePrivateChat": hall.lock_settings_disable_private_chat,
        "lockSettingsDisableNote": hall.lock_settings_disable_note,
        "guestPolicy": hall.guest_policy,
        # disable recording
        "record": hall.record,
        "autoStartRecording": False,
        "allowStartStopRecording": hall.record,
    }

    try:
        xml = execute_api_call("create", hall.instance, **kwargs).parse()
    except RequestFailedError as e:
        return getattr(e, "message", None) or repr(e)


def create(fight):

    signer = signing.Signer(salt="bbb-passwords")

    kwargs = {
        "meetingID": "%s-fr-%d" % (fight.round.tournament.slug, fight.id),
        "name": "%s Round %d Room %s"
        % (fight.round.tournament.name, fight.round.order, fight.room.name),
        "attendeePW": signer.sign("a-%d" % fight.id).replace(":", "-"),
        "moderatorPW": signer.sign("m-%d" % fight.id).replace(":", "-"),
        "maxParticipants": 1000,
        "logoutURL": "https://cc.iypt.org",
        "muteOnStart": True,
        "allowModsToUnmuteUsers": False,
        "lockSettingsDisableCam": False,
        "lockSettingsDisablePrivateChat": False,
        "lockSettingsDisableNote": False,
        "guestPolicy": fight.round.tournament.fight_room_guest_policy,
        # disable recording
        "record": fight.virtual_record,
        "autoStartRecording": False,
        "allowStartStopRecording": fight.virtual_record,
    }

    # set presenter role if assigned
    # presenter = MeetingAttendance.get_presenter_for_meeting(meeting)
    # if presenter:
    #    kwargs['meta_presenter'] = presenter.get_full_name() or presenter.get_username()

    try:
        xml = execute_api_call("create", fight.virtual_server, **kwargs).parse()
    except RequestFailedError as e:
        return getattr(e, "message", None) or repr(e)


def string_to_boolean(string):
    return string.lower() == "true"


def is_meeting_running(fight):
    try:
        return True, string_to_boolean(
            execute_api_call(
                "isMeetingRunning",
                fight.virtual_server,
                meetingID="%s-fr-%d" % (fight.round.tournament.slug, fight.id),
            )
            .parse()
            .find("running")
            .text
        )
    except (AttributeError, RequestFailedError) as e:
        return False, False


def is_hall_running(hall):
    try:
        return True, string_to_boolean(
            execute_api_call(
                "isMeetingRunning",
                hall.instance,
                meetingID="%s-h-%d" % (hall.tournament.slug, hall.id),
            )
            .parse()
            .find("running")
            .text
        )
    except (AttributeError, RequestFailedError) as e:
        return False, False


def _get_atts(xml, trn):
    atts = xml.find("attendees")
    attendees = []
    guests = []
    for att in atts:
        userIDstr = att.find("userID").text
        if userIDstr.startswith("iyptcc_"):
            try:
                uid = int(userIDstr[7:])
                usr = Attendee.objects.get(active_user__user__id=uid, tournament=trn)
                attendees.append(usr)
            except:
                pass
        else:
            name = att.find("fullName").text
            g = BBBGuest.objects.get_or_create(userid=userIDstr, name=name)[0]
            guests.append(g)
    return attendees, guests


def get_hall_attendees(hall):
    kwargs = {"meetingID": "%s-h-%d" % (hall.tournament.slug, hall.id)}
    if hall.instance:
        try:
            xml = execute_api_call("getMeetingInfo", hall.instance, **kwargs).parse()
        except:
            hall.virtual_attendees.clear()
            hall.virtual_guests.clear()
            return

        attendees, guests = _get_atts(xml, hall.tournament)
        hall.virtual_attendees.set(attendees)
        hall.virtual_guests.set(guests)
    else:
        hall.virtual_attendees.clear()
        hall.virtual_guests.clear()


def get_attendees(fight):
    kwargs = {"meetingID": "%s-fr-%d" % (fight.round.tournament.slug, fight.id)}
    if fight.virtual_server:
        try:
            xml = execute_api_call(
                "getMeetingInfo", fight.virtual_server, **kwargs
            ).parse()
        except:
            fight.virtual_attendees.clear()
            fight.virtual_guests.clear()
            return

        attendees, guests = _get_atts(xml, fight.round.tournament)
        fight.virtual_attendees.set(attendees)
        fight.virtual_guests.set(guests)
    else:
        fight.virtual_attendees.clear()
        fight.virtual_guests.clear()


def join(fight, fullName, role=Tournament.BBB_ROLE_GUEST, **kwargs):
    kwargs["meetingID"] = "%s-fr-%d" % (fight.round.tournament.slug, fight.id)
    kwargs["fullName"] = fullName
    kwargs["joinViaHtml5"] = True

    signer = signing.Signer(salt="bbb-passwords")
    # set password according to role
    if role == Tournament.BBB_ROLE_MODERATOR:
        kwargs["password"] = signer.sign("m-%d" % fight.id).replace(":", "-")
    elif role == Tournament.BBB_ROLE_ATTENDEE:
        kwargs["password"] = signer.sign("a-%d" % fight.id).replace(":", "-")
    elif role == Tournament.BBB_ROLE_GUEST:
        kwargs["password"] = signer.sign("a-%d" % fight.id).replace(":", "-")
        kwargs["guest"] = True
    else:
        return None

    try:
        instance = fight.virtual_server
        return get_call_url("join", instance, **kwargs)

    except (AttributeError, RequestFailedError) as e:
        return getattr(e, "message", None) or repr(e)


def join_hall(hall: Hall, fullName, role=Tournament.BBB_ROLE_GUEST, **kwargs):
    kwargs["meetingID"] = "%s-h-%d" % (hall.tournament.slug, hall.id)
    kwargs["fullName"] = fullName
    kwargs["joinViaHtml5"] = True

    signer = signing.Signer(salt="bbb-passwords")
    # set password according to role
    if role == Tournament.BBB_ROLE_MODERATOR:
        kwargs["password"] = signer.sign("hm-%d" % hall.id).replace(":", "-")
    elif role == Tournament.BBB_ROLE_ATTENDEE:
        kwargs["password"] = signer.sign("ha-%d" % hall.id).replace(":", "-")
    elif role == Tournament.BBB_ROLE_GUEST:
        kwargs["password"] = signer.sign("ha-%d" % hall.id).replace(":", "-")
        kwargs["guest"] = True
    else:
        return None

    try:
        instance = hall.instance
        return get_call_url("join", instance, **kwargs)

    except (AttributeError, RequestFailedError) as e:
        return getattr(e, "message", None) or repr(e)
