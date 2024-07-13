import random

import pycountry
from faker import Factory, Faker
from faker.config import AVAILABLE_LOCALES as AL
from unidecode import unidecode

# filter non-country locales
# RESTRICTED_LOCALES = {'ja_JP', 'zh_CN', 'zh_TW', 'fa_IR', 'hi_IN', 'ko_KR', 'ne_NP', ''}
RESTRICTED_LOCALES = {
    "",
}
AVAILABLE_LOCALES = {x for x in AL if len(x) > 2 and x not in RESTRICTED_LOCALES}


class FakePerson:

    def __init__(self, role, locale, gender=None):

        f = Factory.create(locale)

        if gender is None:
            # OMG U ASSUMED MAH GENDAH!!!
            self.gender = random.choice(["m", "f"])
        else:
            self.gender = gender

        self.role = role
        self.locale = locale

        if gender == "m":
            self.pref_first_name = f.first_name_male()
            self.pref_last_name = f.last_name_male()
        elif gender == "f":
            self.pref_first_name = f.first_name_female()
            self.pref_last_name = f.last_name_female()
        else:
            self.pref_first_name = f.first_name()
            self.pref_last_name = f.last_name()

        self.first_name = unidecode(self.pref_first_name).strip()
        self.last_name = unidecode(self.pref_last_name).strip()
        if len(self.last_name) > 29:
            self.last_name = self.last_name[:30]  # Bug in Django 1.* with max_length=30
        username = "%s_%s" % (self.first_name.lower(), self.last_name.lower())
        san_username = ""
        for c in username:
            if c.isalnum() or c in ["_", "-"]:
                san_username += c
        self.username = san_username

        # later we will maybe need an address or so


class FakeTeam:
    def __init__(self, locale=None, members=5):
        if locale is None:
            locale = random.choice(list(AVAILABLE_LOCALES))

        while not hasattr(self, "country"):
            try:
                self.country = pycountry.countries.get(
                    alpha_2=locale.split("_")[1]
                ).name
            except:
                locale = random.choice(list(AVAILABLE_LOCALES))

        print("Team locale:", locale, self.country)
        self.locale = locale
        self.members = []
        for i in range(members):
            self.members.append(FakePerson("member", locale))

        self.teamleaders = [
            FakePerson(random.choice(["teamleader", "juror"]), locale) for i in range(2)
        ]

    # maybe more stuff later


class FakeTournament:

    def __init__(self, host_locale, teams, team_members, indep_jur, local_jur, f_ass=0):
        remaining = list(AVAILABLE_LOCALES)
        self.host_locale = host_locale
        self.host_country = pycountry.countries.get(
            alpha_2=host_locale.split("_")[-1]
        ).name

        self.local_jurors = []
        for j in range(local_jur):
            self.local_jurors.append(FakePerson("local", host_locale))

        self.fight_assistants = []
        for j in range(f_ass):
            self.fight_assistants.append(FakePerson("assistant", host_locale))

        self.teams = []
        self.teams.append(FakeTeam(host_locale, team_members))
        remaining.remove(host_locale)
        countries = []
        for t in range(teams - 1):
            locale = random.choice(remaining)
            team = FakeTeam(locale, team_members)
            while (team.locale not in remaining) or team.country in countries:
                locale = random.choice(remaining)
                team = FakeTeam(locale, team_members)
            remaining.remove(team.locale)
            countries.append(team.country)
            self.teams.append(team)

        self.independent_jurors = []
        for i in range(indep_jur):
            locale = random.choice(self.teams).locale
            self.independent_jurors.append(FakePerson("independent", locale))
            self.independent_jurors[-1].country = pycountry.countries.get(
                alpha_2=self.independent_jurors[-1].locale.split("_")[-1]
            ).name

        self.problems = []
        fake = Faker()
        for p in range(17):
            self.problems.append(
                (p + 1, fake.sentence(nb_words=4), "\n".join(fake.sentences()))
            )


# standalone test
if __name__ == "__main__":
    # test_tourn = FakeTournament('en_GB', 2, 5, 10, 15)
    test_tourn = FakeTournament("zh_CN", 2, 5, 10, 15)

    print(test_tourn.teams[0].members[0].__dict__)
