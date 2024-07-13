from django.dispatch.dispatcher import Signal

from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if user.is_authenticated and user.profile.tournament:
        t = user.profile.tournament
        top_item = MenuItem(60, "Result", "#", icon="fa fa-trophy")
        teams = MenuItem(61, "Teams", "result:teams", route_args={"t_slug": t.slug})
        sched = MenuItem(
            62, "Schedule", "result:schedule", route_args={"t_slug": t.slug}
        )
        slides = MenuItem(63, "Slides", "result:slides", route_args={"t_slug": t.slug})
        plan = MenuItem(64, "Overview", "result:plan", route_args={"t_slug": t.slug})
        rank = MenuItem(65, "Ranking", "result:rank", route_args={"t_slug": t.slug})
        top_item.add_child(teams)
        top_item.add_child(sched)
        top_item.add_child(slides)
        top_item.add_child(plan)
        top_item.add_child(rank)
        sender.add_item(top_item)

    else:
        slug = None
        if hasattr(kwargs["context"]["request"].resolver_match, "kwargs"):
            slug = kwargs["context"]["request"].resolver_match.kwargs.get(
                "t_slug", None
            )

        top_item = MenuItem(60, "Result ", "#", icon="fa fa-trophy")

        list = MenuItem(61, "Tournaments", "result:index")
        top_item.add_child(list)

        if slug:
            teams = MenuItem(62, "Teams", "result:teams", route_args={"t_slug": slug})
            sched = MenuItem(
                63, "Schedule", "result:schedule", route_args={"t_slug": slug}
            )
            plan = MenuItem(64, "Overview", "result:plan", route_args={"t_slug": slug})
            rank = MenuItem(65, "Ranking", "result:rank", route_args={"t_slug": slug})

            top_item.add_child(teams)
            top_item.add_child(sched)
            top_item.add_child(plan)
            top_item.add_child(rank)

        sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
