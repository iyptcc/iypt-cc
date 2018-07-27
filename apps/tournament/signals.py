from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user=kwargs['context']['user']
    if user.is_authenticated and user.profile.tournament:
        t = user.profile.tournament
        if t:
            if user.has_perm("tournament.app_tournament"):
                top_item = MenuItem(500, 'Tournament', '#', icon="fa fa-flag")

                ov = MenuItem(500, 'Settings', '#', icon="fa fa-cog")
                ovgen = MenuItem(501, 'General', 'tournament:overview')
                ovtemp = MenuItem(502, 'Templates', 'tournament:templates')
                ovreg = MenuItem(503, 'Registration', 'tournament:registration')
                ovjury = MenuItem(504, 'Jury', 'tournament:jury')
                ovbank = MenuItem(505, 'Bank', 'tournament:bank')
                problems = MenuItem(520, 'Problems', 'tournament:problems')
                origins = MenuItem(530, 'Origins', 'tournament:origins')
                data = MenuItem(540, 'Data', 'tournament:properties')
                phase = MenuItem(541, 'Phases', 'tournament:phases')
                rights = MenuItem(545, 'Rights', '#', icon="fa fa-shield")
                proles = MenuItem(550, "Roles", "tournament:proles")
                troles = MenuItem(551, "Team Roles", "tournament:troles")
                pgroups = MenuItem(554, "Groups", "tournament:pgroups")
                config = MenuItem(555, "Dump/Restore", "tournament:config_dump")
                ov.add_child(ovgen)
                ov.add_child(ovtemp)
                ov.add_child(ovreg)
                ov.add_child(ovjury)
                ov.add_child(ovbank)
                top_item.add_child(ov)
                top_item.add_child(problems)
                top_item.add_child(origins)
                top_item.add_child(data)
                top_item.add_child(phase)
                rights.add_child(proles)
                rights.add_child(troles)
                rights.add_child(pgroups)
                top_item.add_child(rights)
                top_item.add_child(config)
                sender.add_item(top_item)

Menu.show_signal.connect(my_menuitems_builder)
