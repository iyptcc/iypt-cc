from django.dispatch.dispatcher import Signal

from apps.dashboard.menu import Menu, MenuItem

from .models import PossibleJuror


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user=kwargs['context']['user']
    if user.is_authenticated and user.has_perm("tournament.app_jury") and user.profile.tournament:
        top_item = MenuItem(40, 'Jury', '#', icon="fa fa-balance-scale")

        badges = []
        open_appl = PossibleJuror.objects.filter(tournament=user.profile.tournament,approved_by__isnull=True).count()
        if open_appl > 0:
            badges.append(("%s" % open_appl, MenuItem.COLOR_YELLOW))
        opatr = {"badges": badges}

        possible = MenuItem(41, 'Possible', 'jury:possiblejurors', **opatr)
        persons = MenuItem(42, 'Persons', 'jury:jurors')
        plan = MenuItem(43, 'Plan', 'jury:plan')
        ass = MenuItem(44, 'Assign', 'jury:assign')
        top_item.add_child(possible)
        top_item.add_child(persons)
        top_item.add_child(ass)
        top_item.add_child(plan)
        sender.add_item(top_item)

Menu.show_signal.connect(my_menuitems_builder)
