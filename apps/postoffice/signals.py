from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user=kwargs['context']['user']
    if user.is_authenticated and user.has_perm("tournament.app_postoffice") and user.profile.tournament:
        top_item = MenuItem(480, 'Postoffice', '#', icon="fa fa-envelope-o")
        #li = MenuItem(4501, 'PDFs', 'printer:list')
        #tags = MenuItem(4502, 'Tags', 'printer:tags')
        tmp = MenuItem(4805, 'Templates', 'postoffice:templates')
        top_item.add_child(tmp)
        sender.add_item(top_item)

Menu.show_signal.connect(my_menuitems_builder)
