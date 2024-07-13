from django.dispatch.dispatcher import Signal

from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if user.is_authenticated and user.profile.tournament:
        # if user.has_perm('tournament.app_plan'):
        if user.has_perm("tournament.app_plan"):
            top_item = MenuItem(300, "Plan", "#", icon="fa fa-table")
            plan = MenuItem(31, "Plan", "plan:plan")
            place = MenuItem(33, "Placeholder", "#")
            events = MenuItem(335, "Events", "plan:events")
            pplan = MenuItem(332, "Plan", "plan:placeholder")
            pteams = MenuItem(333, "Teams", "plan:phteams")
            pbeamer = MenuItem(334, "Draw", "plan:phbeamercontrol")
            teams = MenuItem(34, "Teams", "plan:teams")
            persons = MenuItem(32, "Persons", "plan:persons")
            final = MenuItem(36, "Final", "plan:final")
            dump = MenuItem(37, "Export", "plan:jurydata")

            if user.has_perm("plan.import_curiie"):
                curiie = MenuItem(35, "Import", "plan:curiie")
                top_item.add_child(curiie)

            top_item.add_child(teams)
            top_item.add_child(persons)

            top_item.add_child(events)
            place.add_child(pteams)
            place.add_child(pbeamer)
            place.add_child(pplan)

            top_item.add_child(place)

            top_item.add_child(plan)

            top_item.add_child(final)
            top_item.add_child(dump)

            sender.add_item(top_item)
    # Signal.


Menu.show_signal.connect(my_menuitems_builder)
