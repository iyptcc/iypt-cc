from django.dispatch.dispatcher import Signal

from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user=kwargs['context']['user']
    if user.is_authenticated:
        if user.has_perm('tournament.app_schedule'):
            top_item = MenuItem(600, 'Schedule', '#', icon="fa fa-list-ol")
            li = MenuItem(610, 'List', 'schedule:list')
            gen = MenuItem(612, 'Generate', 'schedule:generate')
            top_item.add_child(li)
            top_item.add_child(gen)

            sender.add_item(top_item)

Menu.show_signal.connect(my_menuitems_builder)
