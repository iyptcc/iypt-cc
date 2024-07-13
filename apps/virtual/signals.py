from django.dispatch.dispatcher import Signal

from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if (
        user.is_authenticated
        and user.has_perm("tournament.app_virtual")
        and user.profile.tournament
    ):
        top_item = MenuItem(170, "Virtual", "#", icon="fa fa-globe")
        plan = MenuItem(171, "Overview", "virtual:overview")
        top_item.add_child(plan)
        if user.has_perm("plan.view_fight_operator"):
            mng = MenuItem(173, "Manage", "#")
            rooms = MenuItem(175, "Fight Rooms", "virtual:rooms")
            halls = MenuItem(176, "Halls", "virtual:halls")
            streams = MenuItem(177, "Streams", "virtual:streams")
            mng.add_child(rooms)
            mng.add_child(halls)
            mng.add_child(streams)
            top_item.add_child(mng)
        sender.add_item(top_item)
    # Signal.


Menu.show_signal.connect(my_menuitems_builder)
