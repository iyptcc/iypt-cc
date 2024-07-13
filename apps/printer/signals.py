from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if (
        user.is_authenticated
        and user.has_perm("tournament.app_printer")
        and user.profile.tournament
    ):
        top_item = MenuItem(450, "Printer", "#", icon="fa fa-file-pdf-o")
        li = MenuItem(4501, "PDFs", "printer:list")
        tags = MenuItem(4502, "Tags", "printer:tags")
        tmp = MenuItem(4505, "Templates", "printer:templates")
        top_item.add_child(li)
        top_item.add_child(tags)
        top_item.add_child(tmp)
        sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
