from django.dispatch.dispatcher import Signal

from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user=kwargs['context']['user']
    if user.is_authenticated and user.has_perm("tournament.app_fight") and user.profile.tournament:
        top_item = MenuItem(120, 'Fight', '#', icon="fa fa-bullseye")
        plan = MenuItem(122, 'Overview', 'fight:plan')
        top_item.add_child(plan)
        if user.has_perm("plan.view_fight_operator"):
            mng = MenuItem(123, 'Manage', '#')
            assimng = MenuItem(125, 'Assistants', 'fight:manage')
            validate = MenuItem(126, 'Validate', 'fight:validate')
            pub = MenuItem(127, 'Publish', 'fight:publish')
            mng.add_child(assimng)
            mng.add_child(validate)
            mng.add_child(pub)
            top_item.add_child(mng)
        sender.add_item(top_item)
    #Signal.

Menu.show_signal.connect(my_menuitems_builder)
