from django.dispatch.dispatcher import Signal

from apps.account.models import Attendee, ParticipationRole
from apps.dashboard.menu import Menu, MenuItem
from apps.registration.models import Application
from apps.tournament.models import Tournament

from .utils import persons_data


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class
    user = kwargs["context"]["user"]
    if user.is_authenticated:
        profile_item = MenuItem(30, "Registration", "#", icon="fa fa-address-card")

        req = kwargs["context"]["request"]

        opatr = {}
        if req.session.get("menu-display-%d" % int(30), False) == True:
            badges = []
            open_appl = Application.objects.filter(applicant=user.profile).count()
            if open_appl > 0:
                badges.append(("%s" % open_appl, MenuItem.COLOR_YELLOW))
            opatr = {"badges": badges}
        t_list = MenuItem(31, "My Applications", "registration:applications", **opatr)
        profile_item.add_child(t_list)
        if user.has_perm("registration.manage_data"):
            opatr = {}
            if req.session.get("menu-display-%d" % int(30), False) == True:
                if user.profile.tournament:
                    pdata, opts = persons_data(
                        Attendee.objects.filter(id=user.profile.active.id)
                    )
                    for v in pdata[user.profile.active.id]["data"]:
                        if "list" not in v:
                            v["list"] = []
                    badges = []
                    reqir = len(
                        [
                            x
                            for x in pdata[user.profile.active.id]["data"]
                            if x["value"] in [None, ""]
                            and len(x["list"]) == 0
                            and ("image" not in x)
                            and ("file" not in x)
                            and x["required"]
                        ]
                    )
                    if reqir > 0:
                        badges.append(("%s" % reqir, MenuItem.COLOR_RED))
                    opt = len(
                        [
                            x
                            for x in pdata[user.profile.active.id]["data"]
                            if x["value"] in [None, ""]
                            and len(x["list"]) == 0
                            and ("image" not in x)
                            and ("file" not in x)
                            and x["optional"]
                        ]
                    )
                    if opt > 0:
                        badges.append(("%s" % opt, MenuItem.COLOR_YELLOW))
                    opatr = {"badges": badges}
            t_data = MenuItem(32, "My Data", "registration:attendeeproperty", **opatr)
            profile_item.add_child(t_data)
        if user.has_perm("registration.manage_team"):
            t_teams = MenuItem(33, "Manage Teams", "registration:manageable_teams")
            profile_item.add_child(t_teams)
        if user.has_perm("registration.accept_team"):
            opatr = {}
            if req.session.get("menu-display-%d" % int(30), False) == True:
                open_appl = Application.objects.filter(
                    tournament=user.profile.tournament, origin__isnull=False
                ).count()
                if open_appl > 0:
                    opatr = {
                        "badge": "%s" % open_appl,
                        "badge_color": MenuItem.COLOR_YELLOW,
                    }
            t_listta = MenuItem(
                34, "Team Applications", "registration:list_team_applications", **opatr
            )
            profile_item.add_child(t_listta)
        if user.has_perm("registration.accept_role"):
            opatr = {}
            if req.session.get("menu-display-%d" % int(30), False) == True:
                open_appl = Application.objects.filter(
                    tournament=user.profile.tournament,
                    origin__isnull=True,
                    team__isnull=True,
                ).count()
                if open_appl > 0:
                    opatr = {
                        "badge": "%s" % open_appl,
                        "badge_color": MenuItem.COLOR_YELLOW,
                    }
            t_listra = MenuItem(
                36, "Role Applications", "registration:list_role_applications", **opatr
            )
            profile_item.add_child(t_listra)
        if user.has_perm("registration.view_all_data"):
            t_listra = MenuItem(37, "Data Overview", "registration:overview")
            profile_item.add_child(t_listra)
        sender.add_item(profile_item)


Menu.show_signal.connect(my_menuitems_builder)
