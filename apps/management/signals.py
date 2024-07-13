from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if user.is_authenticated and user.has_perm("tournament.app_management"):
        top_item = MenuItem(700, "Management", "#", icon="fa fa-cog")
        trns = MenuItem(710, "Tournaments", "management:list")
        us = MenuItem(720, "Users", "management:users")
        pro = MenuItem(730, "Profile", "management:properties")
        sys = MenuItem(740, "System Info", "management:system_info")
        fb = MenuItem(741, "Feedback", "management:feedback")
        top_item.add_child(trns)
        top_item.add_child(us)
        top_item.add_child(pro)
        top_item.add_child(sys)
        top_item.add_child(fb)
        sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
