import json

from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError

from apps.jury.models import PossibleJuror
from apps.jury.views import get_previous
from apps.tournament.models import Tournament


class Command(BaseCommand):
    help = "exports all possible jurors for tournament slug"

    def add_arguments(self, parser):
        parser.add_argument("tournament_slug", type=str)

    def handle(self, *args, **options):
        trn = Tournament.objects.get(slug=options["tournament_slug"])
        # self.stdout.write(
        #    self.style.SUCCESS('exporting %s' % trn)
        # )
        pjs = PossibleJuror.objects.filter(tournament=trn)
        data = []
        for p in tqdm(pjs):
            dat = {
                "first_name": p.person.user.first_name,
                "last_name": p.person.user.last_name,
                "username": p.person.user.username,
                "email": p.person.user.email,
                "experience": p.experience,
            }
            previous = get_previous(p)
            pasts = []
            for prev in previous:
                past = {
                    "tournament_slug": prev["attendee"].tournament.slug,
                }
                if "juror" in prev:
                    past_js = []
                    for js in prev["jurorsessions"]:
                        past_js.append(
                            {
                                "role": js["jurorsession"].role.name,
                                "round": js["jurorsession"].fight.round.order,
                                "bias": js.get("bias"),
                            }
                        )

                    past["jurorsessions"] = past_js

                    past["conflicts"] = list(
                        prev["juror"].conflicting.all().values_list("name", flat=True)
                    )

                    past["experience"] = prev["juror"].experience
                    past["local"] = prev["juror"].local
                    past["possible_chair"] = prev["juror"].possible_chair
                past["roles"] = list(
                    prev["attendee"].roles.all().values_list("name", flat=True)
                )
                past["teams"] = {
                    tm.team.origin.name: tm.role.name
                    for tm in prev["attendee"].teammember_set.all()
                }
                pasts.append(past)

            dat["previous"] = pasts
            data.append(dat)

        # print(data)
        self.stdout.write(json.dumps(data, indent=2))
        # self.stdout.write(self.style.SUCCESS('done'))
