from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if user.is_authenticated:
        if user.has_perm("tournament.app_feedback"):
            top_item = MenuItem(46, "Feedback", "#", icon="fa fa-commenting")
            plan = MenuItem(547, "Plan", "feedback:plan")
            top_item.add_child(plan)
            if user.has_perm("feedback.stats"):
                overview = MenuItem(548, "Overview", "feedback:overview")
                top_item.add_child(overview)
            sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
