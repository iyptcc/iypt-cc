from django.dispatch.dispatcher import Signal

from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if (
        user.is_authenticated
        and user.has_perm("tournament.app_bank")
        and user.profile.tournament
    ):
        top_item = MenuItem(550, "Bank", "#", icon="fa fa-bank")
        fee = MenuItem(551, "Fees", "#")
        tfee = MenuItem(552, "Team", "bank:fee_team")
        rfee = MenuItem(553, "Role", "bank:fee_roles")
        pfee = MenuItem(554, "Property", "bank:fee_property")
        acc = MenuItem(555, "Accounts", "bank:accounts")
        bill = MenuItem(560, "Billing", "#")
        bteam = MenuItem(561, "Teams", "bank:bill_teams")
        batt = MenuItem(562, "Attendees", "bank:bill_attendees")

        fee.add_child(tfee)
        fee.add_child(rfee)
        fee.add_child(pfee)
        bill.add_child(bteam)
        bill.add_child(batt)
        top_item.add_child(fee)
        top_item.add_child(acc)
        top_item.add_child(bill)
        sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
