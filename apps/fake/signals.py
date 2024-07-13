from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if user.is_authenticated:
        if user.has_perm("tournament.app_fake"):
            top_item = MenuItem(80, "Fake Data", "#", icon="fa fa-meh-o")
            plan = MenuItem(801, "Actions", "fake:actions")
            imp = MenuItem(802, "Import", "fake:import")
            top_item.add_child(plan)
            top_item.add_child(imp)
            sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
