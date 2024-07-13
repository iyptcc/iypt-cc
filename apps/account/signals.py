from apps.bank.models import Account
from apps.dashboard.menu import Menu, MenuItem
from apps.jury.models import Juror
from apps.tournament.models import Tournament


def my_menuitems_builder(sender, **kwargs):
    # sender is an instance of Menu class
    user = kwargs["context"]["user"]
    if user.is_authenticated:
        profile_item = MenuItem(20, "Profile", "#", icon="fa fa-user")
        t_selector = MenuItem(24, "Tournament", "account:tournament")
        t_profile = MenuItem(23, "Profile", "account:profile")
        profile_item.add_child(t_profile)
        profile_item.add_child(t_selector)
        if Account.objects.filter(
            owners__tournament=user.profile.tournament, owners=user.profile.active
        ).exists():
            t_fin = MenuItem(25, "Finance", "account:accounts")
            profile_item.add_child(t_fin)
        if Juror.objects.filter(attendee=user.profile.active).exists():
            t_jury = MenuItem(25, "Jury", "account:jury")
            profile_item.add_child(t_jury)
        sender.add_item(profile_item)
    else:
        login_item = MenuItem(20, "Login", "login", icon="fa fa-user")
        reg_item = MenuItem(
            21, "Register", "django_registration_register", icon="fa fa-user-plus"
        )
        sender.add_item(login_item)
        sender.add_item(reg_item)

        request = kwargs["context"]["request"]
        loggedin = False
        for t in Tournament.objects.filter(results_access=Tournament.RESULTS_PASSWORD):
            loggedin |= request.session.get("results-auth-%s" % t.slug, False)
        if loggedin:
            profile_item = MenuItem(
                22, "Results Logout", "dashboard:simplelogout", icon="fa fa-sign-out"
            )
            sender.add_item(profile_item)


Menu.show_signal.connect(my_menuitems_builder)
