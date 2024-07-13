from apps.dashboard.menu import Menu, MenuItem


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class

    user = kwargs["context"]["user"]
    if user.is_authenticated and user.profile.tournament:
        t = user.profile.tournament
        if t:
            if user.has_perm("tournament.app_tournament"):
                top_item = MenuItem(500, "Tournament", "#", icon="fa fa-flag")

                ov = MenuItem(500, "Settings", "#", icon="fa fa-cog")
                ovgen = MenuItem(501, "General", "tournament:overview")
                ovtemp = MenuItem(502, "Templates", "tournament:templates")
                ovmail = MenuItem(506, "Mail Templates", "tournament:mailtemplates")
                ovreg = MenuItem(503, "Registration", "tournament:registration")
                ovfb = MenuItem(507, "Feedback", "tournament:feedback")
                ovjury = MenuItem(504, "Jury", "tournament:jury")
                ovbank = MenuItem(505, "Bank", "tournament:bank")
                problems = MenuItem(520, "Problems", "tournament:problems")
                origins = MenuItem(530, "Origins", "tournament:origins")
                caches = MenuItem(535, "Caches", "tournament:caches")
                bbbservers = MenuItem(536, "BBB Server", "tournament:bbbservers")
                fileservers = MenuItem(537, "File Server", "tournament:fileservers")
                grading = MenuItem(538, "Grading", "tournament:grading")
                data = MenuItem(540, "Data", "tournament:properties")
                phase = MenuItem(541, "Phases", "tournament:phases")
                joccupations = MenuItem(5410, "Occupations", "tournament:joccupations")
                feedback = MenuItem(542, "Feedback", "#", icon="fa fa-commenting")
                feedbackgrades = MenuItem(543, "Grades", "tournament:feedbackgrades")
                chaircrit = MenuItem(
                    544, "Criteria", "tournament:chairfeedbackcriteria"
                )
                rights = MenuItem(545, "Rights", "#", icon="fa fa-shield")
                apis = MenuItem(550, "API Users", "tournament:apiusers")
                proles = MenuItem(550, "Roles", "tournament:proles")
                troles = MenuItem(551, "Team Roles", "tournament:troles")
                pgroups = MenuItem(554, "Groups", "tournament:pgroups")
                config = MenuItem(555, "Dump/Restore", "tournament:config_dump")
                ov.add_child(ovgen)
                ov.add_child(ovtemp)
                ov.add_child(ovmail)
                ov.add_child(ovreg)
                ov.add_child(ovfb)
                ov.add_child(ovjury)
                ov.add_child(ovbank)
                top_item.add_child(ov)
                top_item.add_child(problems)
                top_item.add_child(origins)
                top_item.add_child(bbbservers)
                top_item.add_child(fileservers)
                top_item.add_child(grading)
                top_item.add_child(caches)
                top_item.add_child(data)
                top_item.add_child(phase)
                top_item.add_child(joccupations)
                feedback.add_child(feedbackgrades)
                feedback.add_child(chaircrit)
                top_item.add_child(feedback)
                rights.add_child(apis)
                rights.add_child(proles)
                rights.add_child(troles)
                rights.add_child(pgroups)
                top_item.add_child(rights)
                top_item.add_child(config)
                sender.add_item(top_item)


Menu.show_signal.connect(my_menuitems_builder)
