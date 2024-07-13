from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    top_item = MenuItem(800, "About", "#", icon="fa fa-info")
    tos = MenuItem(801, "Terms of Service", "about:tos")
    lic = MenuItem(802, "Attribution", "about:info")
    help = MenuItem(804, "Help", "about:help")

    top_item.add_child(tos)
    top_item.add_child(lic)
    top_item.add_child(help)
    sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
